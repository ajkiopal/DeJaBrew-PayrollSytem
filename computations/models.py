from django.db import models
from employees.models import Employee


class PayrollEmployeeProfile(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="payroll_profile")
    employment_type = models.CharField(max_length=50, blank=True, default="")
    base_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.employee.name}"


class AttendanceSummary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_period_start = models.DateField()
    payroll_period_end = models.DateField()
    total_regular_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_overtime_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_late_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_undertime_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.employee.employee_id} ({self.payroll_period_start} to {self.payroll_period_end})"


class PayrollRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_period_start = models.DateField()
    payroll_period_end = models.DateField()
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_finalized = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "payroll_period_start", "payroll_period_end"],
                name="uniq_payrollrecord_employee_period"
            )
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.payroll_period_start} to {self.payroll_period_end}"
class AdjustmentRecord(models.Model):
    payroll_record = models.ForeignKey(PayrollRecord, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    adjustment_type = models.CharField(max_length=50, default="Manual")
    justification = models.TextField(blank=True, default="")
    admin_id = models.CharField(max_length=50, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Adj {self.amount} for {self.payroll_record}"