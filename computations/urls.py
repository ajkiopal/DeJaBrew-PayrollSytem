from django.urls import path
from . import views

urlpatterns = [
    path("adjustments/", views.adjustments_view, name="payroll_adjustments"),
    path("adjustments/<int:employee_id>/", views.adjustments_view, name="payroll_adjustments_employee"),
    path("generate-summaries/", views.generate_attendance_summaries, name="generate_attendance_summaries"),
]