from decimal import Decimal
from django.db import transaction, models

from employees.models import Employee
from .models import PayrollEmployeeProfile, AttendanceSummary, PayrollRecord, AdjustmentRecord


def compute_gross_from_profile_and_summary(profile: PayrollEmployeeProfile, summary: AttendanceSummary) -> Decimal:
    base_rate = profile.base_hourly_rate
    ot_rate = profile.overtime_hourly_rate

    regular_pay = summary.total_regular_hours * base_rate
    overtime_pay = summary.total_overtime_hours * ot_rate

    late_deduction = summary.total_late_hours * base_rate
    undertime_deduction = summary.total_undertime_hours * base_rate

    gross_pay = regular_pay + overtime_pay + profile.allowances - (late_deduction + undertime_deduction)
    return gross_pay


@transaction.atomic
def build_or_update_payroll_record(employee: Employee, summary: AttendanceSummary, payroll_run=None) -> PayrollRecord:
    profile = PayrollEmployeeProfile.objects.select_for_update().get(employee=employee)

    gross_pay = compute_gross_from_profile_and_summary(profile, summary)

    pr, created = PayrollRecord.objects.get_or_create(
        employee=employee,
        payroll_period_start=summary.payroll_period_start,
        payroll_period_end=summary.payroll_period_end,
        defaults={
            "payroll_run": payroll_run,
            "gross_pay": gross_pay, 
            "net_pay": gross_pay, 
            "is_finalized": False
        },
    )

    pr.gross_pay = gross_pay
    if payroll_run:
        pr.payroll_run = payroll_run

    total_adj = (
        AdjustmentRecord.objects
        .filter(payroll_record=pr)
        .aggregate(total=Sum("amount"))["total"] or Decimal("0") # Changed models.Sum to Sum
    )

    pr.net_pay = gross_pay + total_adj
    
    pr.save()
    return pr