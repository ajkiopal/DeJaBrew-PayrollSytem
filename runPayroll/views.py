import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods

from django.shortcuts import get_object_or_404

from employees.models import Employee as CoreEmployee
from .models import PayPeriod, PayrollRun

# --- Pull from computations app ---
from employees.models import Employee
from computations.models import AttendanceSummary, PayrollRecord, PayrollEmployeeProfile
from computations.services import build_or_update_payroll_record
from computations.views import generate_attendance_summaries


# ✅ Session-based admin permission (matches your existing login system)
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


@admin_required
@require_http_methods(["GET", "POST"])
def payroll_run_create_page(request):
    periods = PayPeriod.objects.filter(status="OPEN").order_by("-start_date")

    if request.method == "POST":
        period_id = request.POST.get("period_id")
        if not period_id:
            messages.error(request, "Select a pay period.")
            return redirect("payroll_run_create")

        period = get_object_or_404(PayPeriod, pk=period_id)

        if period.status != "OPEN":
            messages.error(request, "This pay period is closed.")
            return redirect("payroll_run_create")

        try:
            with transaction.atomic():
                run = PayrollRun.objects.create(
                    period=period,
                    status="RUNNING",
                    created_by=None,  # keep as None since you're not using Django auth
                )

                # generate summaries first
                generate_attendance_summaries(request)

                created_or_updated = 0
                skipped_missing_summary = 0
                skipped_missing_profile = 0

                employees = Employee.objects.filter(is_active=True).order_by("employee_id")

                for emp in employees:
                    if not PayrollEmployeeProfile.objects.filter(employee=emp).exists():
                        skipped_missing_profile += 1
                        continue

                    summary = AttendanceSummary.objects.filter(
                        employee=emp,
                        payroll_period_start=period.start_date,
                        payroll_period_end=period.end_date,
                    ).first()

                    if not summary:
                        skipped_missing_summary += 1
                        continue

                    build_or_update_payroll_record(emp, summary)
                    created_or_updated += 1

                run.status = "COMPLETED"
                run.completed_at = timezone.now()
                run.save()

            messages.success(
                request,
                (
                    f"Payroll run created for period {period.start_date} to {period.end_date}. "
                    f"Computed: {created_or_updated}. "
                    f"Skipped (missing profile): {skipped_missing_profile}. "
                    f"Skipped (missing summary): {skipped_missing_summary}."
                )
            )
            return redirect("payroll_run_detail", run_id=run.id)

        except IntegrityError:
            messages.error(request, "A payroll run already exists for that period.")
            return redirect("payroll_run_create")

    return render(request, "runPayroll/payrollRunCreate.html", {"periods": periods})


@admin_required
def payroll_run_detail(request, run_id):
    run = get_object_or_404(PayrollRun, pk=run_id)

    records = PayrollRecord.objects.filter(
        payroll_period_start=run.period.start_date,
        payroll_period_end=run.period.end_date,
    ).select_related("employee").order_by("employee__employee_id")

    return render(request, "runPayroll/payrollRunDetail.html", {
        "run": run,
        "records": records,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def pay_period_list_create(request):
    periods = PayPeriod.objects.all().order_by("-start_date")

    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        label = request.POST.get("label", "")
        status = request.POST.get("status", "OPEN")

        period = PayPeriod(
            start_date=start_date,
            end_date=end_date,
            label=label,
            status=status,
        )

        try:
            period.full_clean()
            period.save()
            messages.success(request, "Pay period created.")
            return redirect("pay_periods")
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))

    return render(request, "runPayroll/payPeriods.html", {"periods": periods})


@admin_required
@require_http_methods(["POST"])
def pay_period_close(request, period_id):
    period = get_object_or_404(PayPeriod, pk=period_id)
    period.status = "CLOSED"
    period.save()
    messages.success(request, "Pay period closed.")
    return redirect("pay_periods")


@admin_required
def export_payroll_csv(request, run_id):
    run = get_object_or_404(PayrollRun, pk=run_id)
    
    # We filter records that fall WITHIN the period dates
    records = PayrollRecord.objects.filter(
        payroll_period_start__gte=run.period.start_date,
        payroll_period_end__lte=run.period.end_date
    ).select_related('employee')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Master_Payroll_{run.period}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Gross Pay', 'Net Pay'])

    for rec in records:
        writer.writerow([
            f"{rec.employee.employee_id:04d}", 
            rec.employee.name, 
            rec.gross_pay, 
            rec.net_pay
        ])

    return response

@admin_required
def export_individual_payslip(request, record_id):
    # 1. Get the specific record for one person
    record = get_object_or_404(PayrollRecord, pk=record_id)
    
    # 2. Get their attendance for the breakdown
    summary = AttendanceSummary.objects.filter(
        employee=record.employee,
        payroll_period_start=record.payroll_period_start,
        payroll_period_end=record.payroll_period_end
    ).first()

    # 3. Setup Response
    filename = f"Payslip_{record.employee.employee_id}_{record.payroll_period_end}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    
    # 4. Format as a "Slip" rather than a table
    writer.writerow(['DE JABREW PAYROLL SLIP'])
    writer.writerow(['Employee:', record.employee.name])
    writer.writerow(['Period:', f"{record.payroll_period_start} to {record.payroll_period_end}"])
    writer.writerow([]) # Empty line
    writer.writerow(['EARNINGS', 'AMOUNT'])
    writer.writerow(['Regular Hours', summary.total_regular_hours if summary else 0])
    writer.writerow(['Gross Pay', record.gross_pay])
    writer.writerow(['Net Pay', record.net_pay])
    
    return response