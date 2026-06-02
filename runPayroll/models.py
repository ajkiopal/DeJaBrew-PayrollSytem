from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q


class PayPeriod(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("CLOSED", "Closed"),
    ]

    start_date = models.DateField()
    end_date = models.DateField()
    label = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Ensure start date is not after end date
        if self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")

        # Prevent overlapping pay periods
        overlapping = PayPeriod.objects.filter(
            Q(start_date__lte=self.end_date) &
            Q(end_date__gte=self.start_date)
        ).exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError("This pay period overlaps with an existing one.")

    def __str__(self):
        if self.label:
            return self.label
        return f"{self.start_date} to {self.end_date}"


class PayrollRun(models.Model):
    STATUS_CHOICES = [
        ("RUNNING", "Running"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    period = models.ForeignKey(PayPeriod, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="RUNNING")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["period"], name="unique_payroll_run_per_period")
        ]

    def __str__(self):
        return f"Payroll Run for {self.period} - {self.status}"