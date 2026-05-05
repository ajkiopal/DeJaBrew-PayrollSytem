from django.db import models
from employees.models import Employee


class ScheduleEvent(models.Model):
    STATUS_CHOICES = [
        ("Posted", "Posted"),
        ("Unposted", "Unposted"),
    ]

    title = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    assigned_employees = models.ManyToManyField(Employee, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Posted")

    def __str__(self):
        return f"{self.title} - {self.status}"