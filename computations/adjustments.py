"""
adjustments.py

Handles payroll adjustments:
- Validates admin input
- Applies adjustments to PayrollComputation
- Generates audit logs for each adjustment
"""

from datetime import datetime
from .payroll_models import PayrollComputation, PayrollAdjustment, PayrollAuditLog


def apply_adjustment(payroll, adjustment: PayrollAdjustment) -> PayrollAuditLog:
    """
    Apply an adjustment to a PayrollComputation instance without
    resetting previous adjustments. Returns a PayrollAuditLog entry.

    Args:
        payroll (PayrollComputation): The payroll record to update.
        adjustment (PayrollAdjustment): The adjustment to apply.

    Returns:
        PayrollAuditLog: Record of the adjustment applied.
    """
    # Step 1: Capture old values for audit purposes
    old_values = {
        "net_pay": payroll.net_pay,
        "total_adjustments": payroll.total_adjustments
    }

    # Step 2: Update payroll totals
    payroll.total_adjustments += adjustment.amount
    payroll.net_pay = payroll.gross_pay + payroll.total_adjustments

    # Step 3: Create audit log
    audit_log = PayrollAuditLog(
        log_id=1,  # Replace with real ID generator in production
        employee_id=payroll.employee_id,
        payroll_period_start=payroll.payroll_period_start,
        payroll_period_end=payroll.payroll_period_end,
        admin_id=adjustment.admin_id,
        timestamp=adjustment.timestamp or datetime.now(),
        old_values=old_values,
        new_values={
            "net_pay": payroll.net_pay,
            "total_adjustments": payroll.total_adjustments
        },
        justification=adjustment.justification
    )

    # Step 4: Return audit log for UI / confirmation
    return audit_log