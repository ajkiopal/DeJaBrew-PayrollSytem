from django.db import models
from computations.models import PayrollRecord

class Payslip(models.Model):
    # Links to the record created in the computations app
    payroll_record = models.OneToOneField(
        PayrollRecord, 
        on_delete=models.CASCADE, 
        related_name="payslip"
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"Payslip for {self.payroll_record.employee.name}"