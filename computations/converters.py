"""
converters.py

Handles conversion between Django database models and payroll computation models.
To ensure safe manipulation of data, i separated models.py and payroll_models.py
so all the data manipulated in payroll_models will not affect models.py
"""

# Import Django models
from .models import Employee, AttendanceSummary

# Import your computation logic classes
from .payroll_models import PlaceholderEmployee, PlaceholderAttendanceSummary


# Employee conversion
def convert_employee_to_placeholder(django_employee: Employee) -> PlaceholderEmployee:
    """
    Converts a Django Employee object into a PlaceholderEmployee
    suitable for payroll computations.
    """
    return PlaceholderEmployee(
        employee_id=django_employee.employee_id,
        full_name=django_employee.full_name,
        employment_type=getattr(django_employee, "employment_type", "Unknown"),
        base_hourly_rate=float(django_employee.base_hourly_rate),
        overtime_hourly_rate=float(django_employee.overtime_hourly_rate),
        allowances=float(getattr(django_employee, "allowances", 0.0))
    )


# Attendance conversion
def convert_attendance_to_placeholder(django_attendance: AttendanceSummary) -> PlaceholderAttendanceSummary:
    """
    Converts a Django AttendanceSummary object into a PlaceholderAttendanceSummary
    suitable for payroll computations.
    """
    return PlaceholderAttendanceSummary(
        employee_id=django_attendance.employee.id,
        payroll_period_start=str(django_attendance.payroll_period_start),
        payroll_period_end=str(django_attendance.payroll_period_end),
        total_regular_hours=float(django_attendance.total_regular_hours),
        total_overtime_hours=float(django_attendance.total_overtime_hours),
        total_late_hours=float(django_attendance.total_late_hours),
        total_undertime_hours=float(django_attendance.total_undertime_hours)
    )