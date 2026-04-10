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
def build_or_update_payroll_record(employee: Employee, summary: AttendanceSummary) -> PayrollRecord:
    """
    Ensures PayrollRecord exists for employee+period and updates gross/net using current rules + saved adjustments.
    Returns the PayrollRecord (source of truth for Payroll Run app).
    """
    profile = PayrollEmployeeProfile.objects.select_for_update().get(employee=employee)

    gross_pay = compute_gross_from_profile_and_summary(profile, summary)

    pr, _ = PayrollRecord.objects.get_or_create(
        employee=employee,
        payroll_period_start=summary.payroll_period_start,
        payroll_period_end=summary.payroll_period_end,
        defaults={"gross_pay": gross_pay, "net_pay": gross_pay, "is_finalized": False},
    )

    # Update gross
    pr.gross_pay = gross_pay

    # Sum adjustments
    total_adj = (
        AdjustmentRecord.objects
        .filter(payroll_record=pr)
        .aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    )
    pr.net_pay = gross_pay + total_adj
    pr.save()
    return pr