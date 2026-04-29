from decimal import Decimal, InvalidOperation
from datetime import timedelta, date
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.db.models import Sum

from attendance.models import Attendance as RawAttendance
from employees.models import Employee as CoreEmployee
from .models import (
    AttendanceSummary,
    PayrollRecord,
    AdjustmentRecord,
)

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        emp_id = request.session.get("employee_id")
        if not emp_id:
            return redirect("login")

        emp = CoreEmployee.objects.filter(employee_id=emp_id, is_active=True).first()
        if not emp:
            request.session.flush()
            return redirect("login")

        if emp.role not in ("Admin/Manager", "Manager"):
            return HttpResponseForbidden("Admins only.")

        request.current_employee = emp
        return view_func(request, *args, **kwargs)
    return wrapper


def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _compute_payroll(employee, summary: AttendanceSummary):
    """
    Computes payroll using the salary_rate (hourly) from the Employee model.
    Includes PH Government Deductions and dynamic period dates.
    """
    base_rate = _to_decimal(employee.salary_rate) 
    ot_rate = base_rate * Decimal("1.25") 

    reg_hours = _to_decimal(summary.total_regular_hours)
    ot_hours = _to_decimal(summary.total_overtime_hours)
    late_hours = _to_decimal(summary.total_late_hours)
    undertime_hours = _to_decimal(summary.total_undertime_hours)

    # 1. Calculate Earnings
    regular_pay = reg_hours * base_rate
    overtime_pay = ot_hours * ot_rate
    gross_earnings = regular_pay + overtime_pay

    # 2. PH Government Deductions
    pagibig = Decimal("200.00") if regular_pay > 0 else Decimal("0.00")
    philhealth = regular_pay * Decimal("0.025")
    sss = regular_pay * Decimal("0.05")
    total_gov_deductions = pagibig + philhealth + sss

    # 3. Tardiness Deductions
    late_deduction = late_hours * base_rate
    undertime_deduction = undertime_hours * base_rate

    total_deductions = late_deduction + undertime_deduction + total_gov_deductions
    gross_pay_after_deductions = gross_earnings - total_deductions

    return {
        "payroll_period_start": summary.payroll_period_start,
        "payroll_period_end": summary.payroll_period_end,
        "total_hours": reg_hours,
        "regular_pay": round(regular_pay, 2),
        "overtime_pay": round(overtime_pay, 2),
        "pagibig": round(pagibig, 2),
        "philhealth": round(philhealth, 2),
        "sss": round(sss, 2),
        "total_gov_deductions": round(total_gov_deductions, 2),
        "gross_earnings": round(gross_earnings, 2), 
        "gross_pay": round(gross_pay_after_deductions, 2), 
    }


@admin_required
@require_http_methods(["GET", "POST"])
def adjustments_view(request, employee_id=None):
    employees = list(CoreEmployee.objects.filter(is_active=True).order_by("employee_id"))

    if not employees:
        return render(request, "computations/adjustments.html", {"error_msg": "No employees found."})

    selected_id = employee_id or request.POST.get("employee_id") or employees[0].employee_id
    selected_employee = next((e for e in employees if str(e.employee_id) == str(selected_id)), employees[0])

    if not selected_employee.salary_rate or selected_employee.salary_rate <= 0:
        return render(request, "computations/adjustments.html", {
            "employees": employees,
            "selected_employee": selected_employee,
            "error_msg": f"Hourly salary rate not set for {selected_employee.name}."
        })

    summary = (
        AttendanceSummary.objects
        .filter(employee=selected_employee)
        .order_by("-payroll_period_end")
        .first()
    )

    if not summary:
        return render(request, "computations/adjustments.html", {
            "employees": employees,
            "selected_employee": selected_employee,
            "error_msg": f"No attendance summary found for {selected_employee.name}."
        })

    computed = _compute_payroll(selected_employee, summary)

    # Automatically creates or updates the record based on the summary dates
    payroll_record, _ = PayrollRecord.objects.get_or_create(
        employee=selected_employee,
        payroll_period_start=computed["payroll_period_start"],
        payroll_period_end=computed["payroll_period_end"],
        defaults={"gross_pay": computed["gross_pay"], "net_pay": computed["gross_pay"]}
    )
    payroll_record.gross_pay = computed["gross_pay"]
    payroll_record.save()

    if request.method == "POST" and request.POST.get("amount"):
        amount = _to_decimal(request.POST.get("amount"))
        justification = (request.POST.get("justification") or "").strip()

        if not justification:
            messages.error(request, "Justification is required.")
        else:
            AdjustmentRecord.objects.create(
                payroll_record=payroll_record,
                amount=amount,
                adjustment_type="Manual",
                justification=justification,
                admin_id=str(request.current_employee.employee_id),
            )
            messages.success(request, "Adjustment applied successfully.")

    past_adjustments = list(AdjustmentRecord.objects.filter(payroll_record=payroll_record).order_by("-timestamp"))
    total_adj = sum((_to_decimal(a.amount) for a in past_adjustments), Decimal("0"))
    final_net = computed["gross_pay"] + total_adj

    payroll_record.net_pay = final_net
    payroll_record.save()

    return render(request, "computations/adjustments.html", {
        "employees": employees,
        "selected_employee": selected_employee,
        "payroll": {**computed, "total_adjustments": total_adj, "net_pay": final_net},
        "past_adjustments": past_adjustments,
    })


def _ceil_to_period(d: date):
    """
    Fixed: Determines period based on the input date (e.g., April).
    """
    if d.day <= 15:
        return d.replace(day=1), d.replace(day=15)
    
    # Get last day of the month
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(days=1)
    return d.replace(day=16), end_of_month


@admin_required
@require_http_methods(["POST"])
def generate_attendance_summaries(request):
    """
    1. Processes Raw Logs into Summaries (Hours).
    2. Immediately processes Summaries into PayrollRecords (Money/Payslips).
    """
    logs = RawAttendance.objects.all().order_by("employee_id", "start_date_time")

    if not logs.exists():
        messages.info(request, "No attendance records found yet. Upload a CSV first.")
        return redirect("upload_csv")

    buckets = {}
    for row in logs:
        if not row.start_date_time or not row.end_date_time:
            continue
        p_start, p_end = _ceil_to_period(row.start_date_time.date())
        key = (str(row.employee_id), p_start, p_end)
        buckets.setdefault(key, Decimal("0"))
        delta = row.end_date_time - row.start_date_time
        buckets[key] += Decimal(str(delta.total_seconds())) / Decimal("3600")

    created_summaries = 0
    created_payslips = 0

    for (emp_id_str, p_start, p_end), total_hours in buckets.items():
        emp = CoreEmployee.objects.filter(employee_id=emp_id_str, is_active=True).first()
        if not emp:
            continue

        # 1. Create/Update the Hours Summary
        summary, _ = AttendanceSummary.objects.update_or_create(
            employee=emp,
            payroll_period_start=p_start,
            payroll_period_end=p_end,
            defaults={"total_regular_hours": round(total_hours, 2)}
        )
        created_summaries += 1

        # 2. Create the Payslip Record so it shows in the Master List
        computed = _compute_payroll(emp, summary)
        
        PayrollRecord.objects.update_or_create(
            employee=emp,
            payroll_period_start=p_start,
            payroll_period_end=p_end,
            defaults={
                "gross_pay": computed["gross_pay"],
                "net_pay": computed["gross_pay"]  # Net starts as Gross before adjustments
            }
        )
        created_payslips += 1

    messages.success(
        request, 
        f"Payroll Generated! Summaries: {created_summaries}, Payslips: {created_payslips}."
    )
    # Redirect straight to Master List
    return redirect("admin_payslip_list")