from django.db import models
from scheduling.models import ScheduleEvent


class StaffRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    REQUEST_TYPE_CHOICES = [
        ("Schedule Change", "Schedule Change"),
        ("Overtime", "Overtime"),
    ]

    employee_id = models.IntegerField()
    employee_name = models.CharField(max_length=100)

    request_type = models.CharField(max_length=100, choices=REQUEST_TYPE_CHOICES)

    assigned_schedule = models.ForeignKey(
        ScheduleEvent,
        on_delete=models.CASCADE,
        related_name="staff_requests"
    )

    overtime_hours = models.PositiveIntegerField(null=True, blank=True)

    new_start_time = models.TimeField(null=True, blank=True)
    new_end_time = models.TimeField(null=True, blank=True)

    reason = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_id} - {self.employee_name} - {self.request_type}"