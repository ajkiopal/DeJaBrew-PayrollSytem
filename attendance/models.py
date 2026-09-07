from django.db import models
from employees.models import Employee

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date_time = models.DateTimeField()
    end_date_time = models.DateTimeField()
    source_system = models.CharField(max_length=50, default="UTAK", null=True, blank=True)

    def __str__(self):
        return f"Employee {self.employee_id} - {self.start_date_time.date()}"


class ImportHistory(models.Model):
    date_uploaded = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="Completed")

    def __str__(self):
        return f"Import on {self.date_uploaded.date()} - {self.filename}"