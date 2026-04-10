from decimal import Decimal, InvalidOperation
from datetime import timedelta, date
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_datetime
from django.db.models import Sum

from attendance.models import Attendance as RawAttendance

from employees.models import Employee as CoreEmployee
from .models import (
    PayrollEmployeeProfile,
    AttendanceSummary,
    PayrollRecord,
    AdjustmentRecord,
)

# --- Permission (uses your existing session login; no login changes needed) ---
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


def _compute_payroll(profile: PayrollEmployeeProfile, summary: AttendanceSummary):
    """
    Pure computation based on DB data. Returns a dict ready for template.
    You can swap formula later without touching views/templates.
    """
    base_rate = _to_decimal(profile.base_hourly_rate)
    ot_rate = _to_decimal(profile.overtime_hourly_rate)
    allowances = _to_decimal(profile.allowances)

    reg_hours = _to_decimal(summary.total_regular_hours)
    ot_hours = _to_decimal(summary.total_overtime_hours)
    late_hours = _to_decimal(summary.total_late_hours)
    undertime_hours = _to_decimal(summary.total_undertime_hours)

    # Simple, transparent rules (edit as your rubric requires)
    regular_pay = reg_hours * base_rate
    overtime_pay = ot_hours * ot_rate

    # Late/undertime deductions: rate * hours (common demo approach)
    late_deduction = late_hours * base_rate
    undertime_deduction = undertime_hours * base_rate

    gross_pay = regular_pay + overtime_pay + allowances - (late_deduction + undertime_deduction)

    return {
        "payroll_period_start": summary.payroll_period_start,
        "payroll_period_end": summary.payroll_period_end,
        "regular_pay": regular_pay,
        "overtime_pay": overtime_pay,
        "late_deduction": late_deduction,
        "undertime_deduction": undertime_deduction,
        "gross_pay": gross_pay,
    }


@admin_required
@require_http_methods(["GET", "POST"])
def adjustments_view(request, employee_id=None):
    # 1) Real employees (from employees app)
    employees = list(CoreEmployee.objects.filter(is_active=True).order_by("employee_id"))

    if not employees:
        return render(request, "computations/adjustments.html", {
            "employees": [],
            "selected_employee": None,
            "payroll": None,
            "past_adjustments": [],
            "audit_log": None,
            "error_msg": "No employees found yet. Add employees first.",
        })

    # 2) Pick selected employee (URL param > GET/POST > first employee)
    selected_id = employee_id

    if request.method == "POST":
        posted_id = request.POST.get("employee_id")
        if posted_id:
            try:
                selected_id = int(posted_id)
            except ValueError:
                selected_id = None

    if selected_id is None:
        selected_id = employees[0].employee_id

    selected_employee = next((e for e in employees if e.employee_id == selected_id), employees[0])

    # 3) Pull payroll profile (rates) for selected employee
    profile = PayrollEmployeeProfile.objects.filter(employee=selected_employee).first()
    if not profile:
        return render(request, "computations/adjustments.html", {
            "employees": employees,
            "selected_employee": selected_employee,
            "payroll": None,
            "past_adjustments": [],
            "audit_log": None,
            "error_msg": (
                f"No payroll profile found for {selected_employee.name}. "
                "Create PayrollEmployeeProfile first (rates/allowances)."
            ),
        })

    # 4) Pull attendance summary (hours) for selected employee
    # For demo: use the most recent payroll period. (No hardcoding dates.)
    summary = (
        AttendanceSummary.objects
        .filter(employee=selected_employee)
        .order_by("-payroll_period_end", "-payroll_period_start")
        .first()
    )

    if not summary:
        return render(request, "computations/adjustments.html", {
            "employees": employees,
            "selected_employee": selected_employee,
            "payroll": None,
            "past_adjustments": [],
            "audit_log": None,
            "error_msg": (
                f"No attendance summary found for {selected_employee.name}. "
                "Import attendance + generate summaries first."
            ),
        })

    # 5) Compute payroll (pure computation)
    computed = _compute_payroll(profile, summary)

    # 6) Create/Get PayrollRecord for this employee+period (so adjustments have something to attach to)
    payroll_record, _created = PayrollRecord.objects.get_or_create(
        employee=selected_employee,
        payroll_period_start=computed["payroll_period_start"],
        payroll_period_end=computed["payroll_period_end"],
        defaults={
            "gross_pay": computed["gross_pay"],
            "net_pay": computed["gross_pay"],
            "is_finalized": False,
        }
    )

    # If gross pay formula changed, keep record updated (safe for demo)
    payroll_record.gross_pay = computed["gross_pay"]
    payroll_record.save(update_fields=["gross_pay"])

    audit_log = None

    # 7) If POST has an adjustment, save it to DB (no hardcoded admin_id)
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
                admin_id=str(request.current_employee.employee_id),  # ✅ from session-authenticated user
            )
            messages.success(request, "Adjustment applied successfully.")

    # 8) Rebuild totals from DB (sum all adjustments)
    past_adjustments = list(
        AdjustmentRecord.objects
        .filter(payroll_record=payroll_record)
        .order_by("-timestamp")
    )

    total_adjustments = sum((_to_decimal(a.amount) for a in past_adjustments), Decimal("0"))
    net_pay = computed["gross_pay"] + total_adjustments

    # Save net_pay to payroll record
    payroll_record.net_pay = net_pay
    payroll_record.save(update_fields=["net_pay"])

    # Final payload to template
    payroll = {
        **computed,
        "total_adjustments": total_adjustments,
        "net_pay": net_pay,
    }

    return render(request, "computations/adjustments.html", {
        "employees": employees,
        "selected_employee": selected_employee,
        "payroll": payroll,
        "past_adjustments": past_adjustments,
        "audit_log": audit_log,
        "error_msg": "",
    })

def _ceil_to_period(d: date, days: int = 15):
    """
    Simple payroll period rule for demo:
    - 1st–15th
    - 16th–end of month
    """
    if d.day <= 15:
        return d.replace(day=1), d.replace(day=15)
    # end of month:
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_month = next_month - timedelta(days=1)
    return d.replace(day=16), end_month


@admin_required
@require_http_methods(["POST"])
def generate_attendance_summaries(request):
    """
    Builds/updates computations.AttendanceSummary from attendance.Attendance raw logs.
    No hardcoding. Safe to run multiple times (upsert behavior).
    """
    # Optional: allow generating for all data, or a date range
    # For demo, we’ll just process everything in RawAttendance.
    logs = RawAttendance.objects.all().order_by("employee_id", "start_date_time")

    if not logs.exists():
        messages.info(request, "No attendance records found yet. Upload a CSV first.")
        return redirect("upload_csv")

    created = 0
    updated = 0
    skipped = 0

    # We'll aggregate per (employee_id, period_start, period_end)
    buckets = {}

    for row in logs:
        # row.start_date_time and end_date_time should already be datetimes
        if not row.start_date_time or not row.end_date_time:
            skipped += 1
            continue

        # Choose payroll period based on start_date_time date
        start_day = row.start_date_time.date()
        period_start, period_end = _ceil_to_period(start_day)

        key = (int(row.employee_id), period_start, period_end)
        buckets.setdefault(key, Decimal("0"))

        # hours = (end - start) in hours
        delta = row.end_date_time - row.start_date_time
        hours = Decimal(str(delta.total_seconds())) / Decimal("3600")
        if hours < 0:
            skipped += 1
            continue

        buckets[key] += hours

    # Now write into AttendanceSummary
    for (emp_id, p_start, p_end), total_hours in buckets.items():
        # Map raw attendance employee_id -> employees.Employee.employee_id
        emp = CoreEmployee.objects.filter(employee_id=emp_id, is_active=True).first()
        if not emp:
            skipped += 1
            continue

        # For demo: treat all hours as regular hours.
        # You can later split into overtime/late/undertime if you have rules.
        obj, was_created = AttendanceSummary.objects.update_or_create(
            employee=emp,
            payroll_period_start=p_start,
            payroll_period_end=p_end,
            defaults={
                "total_regular_hours": total_hours,
                "total_overtime_hours": Decimal("0"),
                "total_late_hours": Decimal("0"),
                "total_undertime_hours": Decimal("0"),
            }
        )

        if was_created:
            created += 1
        else:
            updated += 1

    messages.success(
        request,
        f"Attendance summaries generated. Created: {created}, Updated: {updated}, Skipped: {skipped}."
    )
    return redirect("payroll_adjustments")