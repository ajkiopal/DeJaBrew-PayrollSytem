"""
payroll_models.py

Pure computation models. Framework-independent.
"""

class PlaceholderEmployee:
    def __init__(self, employee_id, full_name, employment_type, base_hourly_rate, overtime_hourly_rate, allowances=0.0):
        self.employee_id = employee_id
        self.full_name = full_name
        self.employment_type = employment_type
        self.base_hourly_rate = base_hourly_rate
        self.overtime_hourly_rate = overtime_hourly_rate
        self.allowances = allowances


class PlaceholderAttendanceSummary:
    def __init__(self, employee_id, payroll_period_start, payroll_period_end,
                 total_regular_hours, total_overtime_hours, total_late_hours, total_undertime_hours):
        self.employee_id = employee_id
        self.payroll_period_start = payroll_period_start
        self.payroll_period_end = payroll_period_end
        self.total_regular_hours = total_regular_hours
        self.total_overtime_hours = total_overtime_hours
        self.total_late_hours = total_late_hours
        self.total_undertime_hours = total_undertime_hours


class PayrollComputation:
    def __init__(self, employee_id, payroll_period_start, payroll_period_end,
                 regular_pay, overtime_pay, late_deduction, undertime_deduction,
                 gross_pay, total_adjustments, net_pay):
        self.employee_id = employee_id
        self.payroll_period_start = payroll_period_start
        self.payroll_period_end = payroll_period_end
        self.regular_pay = regular_pay
        self.overtime_pay = overtime_pay
        self.late_deduction = late_deduction
        self.undertime_deduction = undertime_deduction
        self.gross_pay = gross_pay
        self.total_adjustments = total_adjustments
        self.net_pay = net_pay

    def __repr__(self):
        return f"PayrollComputation(employee_id={self.employee_id}, net_pay={self.net_pay})"


class PayrollAdjustment:
    def __init__(self, adjustment_id, employee_id, payroll_period_start, payroll_period_end,
                 amount, adjustment_type, justification, admin_id, timestamp):
        self.adjustment_id = adjustment_id
        self.employee_id = employee_id
        self.payroll_period_start = payroll_period_start
        self.payroll_period_end = payroll_period_end
        self.amount = amount
        self.adjustment_type = adjustment_type
        self.justification = justification
        self.admin_id = admin_id
        self.timestamp = timestamp

    def __repr__(self):
        return f"PayrollAdjustment(employee_id={self.employee_id}, amount={self.amount})"


class PayrollAuditLog:
    def __init__(self, log_id, employee_id, payroll_period_start, payroll_period_end,
                 admin_id, timestamp, old_values, new_values, justification):
        self.log_id = log_id
        self.employee_id = employee_id
        self.payroll_period_start = payroll_period_start
        self.payroll_period_end = payroll_period_end
        self.admin_id = admin_id
        self.timestamp = timestamp
        self.old_values = old_values
        self.new_values = new_values
        self.justification = justification

    def __repr__(self):
        return f"PayrollAuditLog(employee_id={self.employee_id}, admin_id={self.admin_id})"