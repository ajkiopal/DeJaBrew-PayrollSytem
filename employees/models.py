from datetime import date
from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [
        ("Admin/Manager", "Admin"),
        ("Manager", "Manager"),
        ("Staff", "Staff"),
    ]

    # ID Number – auto-generated
    employee_id = models.AutoField(primary_key=True)

    # UC-04 columns
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=13) 
    date_hired = models.DateField(default=date.today)  
    job_title = models.CharField(max_length=25)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    salary_rate = models.DecimalField(max_digits=10, decimal_places=2)

    # UC-05 credentials created during Add Employee
    password_hash = models.CharField(max_length=255)
    must_change_password = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"