"""
calculator.py

Pure payroll computation engine.
Takes PlaceholderEmployee and PlaceholderAttendanceSummary objects,
calculates payroll (regular pay, overtime, deductions, gross/net pay),
and returns a PayrollComputation object.
"""

from .payroll_models import PayrollComputation

# constants (for testing / defaults) feel free to change
LATE_DEDUCTION_RATE = 1       # Deduction per late hour (could be employee base rate)
UNDERTIME_DEDUCTION_RATE = 1  # Deduction per undertime hour (could be employee base rate)


def generate_payroll(employee, attendance):
    """
    Generates a PayrollComputation object for a single employee and attendance record.
    
    employee: PlaceholderEmployee
    attendance: PlaceholderAttendanceSummary
    return: PayrollComputation
    """

    #compute regular pay
    regular_pay = attendance.total_regular_hours * employee.base_hourly_rate

    #compute overtime pay
    overtime_pay = attendance.total_overtime_hours * employee.overtime_hourly_rate

    #compute deductions
    late_deduction = attendance.total_late_hours * employee.base_hourly_rate * LATE_DEDUCTION_RATE
    undertime_deduction = attendance.total_undertime_hours * employee.base_hourly_rate * UNDERTIME_DEDUCTION_RATE

    #compute gross pay (before adjustments)
    gross_pay = regular_pay + overtime_pay + employee.allowances - (late_deduction + undertime_deduction)

    #for now, total adjustments = 0
    total_adjustments = 0.0

    #net pay = gross pay + adjustments
    net_pay = gross_pay + total_adjustments

    #return PayrollComputation object
    return PayrollComputation(
        employee_id=employee.employee_id,
        payroll_period_start=attendance.payroll_period_start,
        payroll_period_end=attendance.payroll_period_end,
        regular_pay=regular_pay,
        overtime_pay=overtime_pay,
        late_deduction=late_deduction,
        undertime_deduction=undertime_deduction,
        gross_pay=gross_pay,
        total_adjustments=total_adjustments,
        net_pay=net_pay
    )