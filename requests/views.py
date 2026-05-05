from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import StaffRequest
from scheduling.models import ScheduleEvent


def admin_requests_home(request):
    requests = StaffRequest.objects.all().order_by("-created_at")

    return render(request, "requests/admin_requests.html", {
        "requests": requests,
    })


def staff_requests_home(request):
    employee_id = request.session.get("employee_id")

    requests = StaffRequest.objects.filter(
        employee_id=employee_id
    ).select_related("assigned_schedule").order_by("-created_at")

    return render(request, "requests/staff_requests.html", {
        "requests": requests,
    })


def staff_request_create(request):
    employee_id = request.session.get("employee_id")
    employee_name = request.session.get("employee_name")

    if not employee_id:
        return redirect("login")

    assigned_schedules = ScheduleEvent.objects.filter(
        assigned_employees__employee_id=employee_id,
        status="Posted"
    ).distinct().order_by("date", "start_time")

    errors = {}
    old = {}

    if request.method == "POST":
        request_type = request.POST.get("request_type", "").strip()
        assigned_schedule_id = request.POST.get("assigned_schedule", "").strip()
        overtime_hours = request.POST.get("overtime_hours", "").strip()
        new_start_time = request.POST.get("new_start_time", "").strip()
        new_end_time = request.POST.get("new_end_time", "").strip()
        reason = request.POST.get("reason", "").strip()

        old = {
            "request_type": request_type,
            "assigned_schedule": assigned_schedule_id,
            "overtime_hours": overtime_hours,
            "new_start_time": new_start_time,
            "new_end_time": new_end_time,
            "reason": reason,
        }

        if not request_type:
            errors["request_type"] = "Please select a request type."

        if request_type not in ["Schedule Change", "Overtime"]:
            errors["request_type"] = "Please choose Schedule Change or Overtime."

        if not assigned_schedule_id:
            errors["assigned_schedule"] = "Please select one assigned schedule."

        assigned_schedule = None
        if assigned_schedule_id:
            assigned_schedule = ScheduleEvent.objects.filter(
                id=assigned_schedule_id,
                assigned_employees__employee_id=employee_id,
                status="Posted"
            ).first()

            if not assigned_schedule:
                errors["assigned_schedule"] = "Invalid schedule selected."

        if request_type == "Overtime":
            if not overtime_hours:
                errors["overtime_hours"] = "Please enter overtime hours."
            else:
                try:
                    overtime_hours = int(overtime_hours)
                    if overtime_hours < 1:
                        errors["overtime_hours"] = "Overtime must be at least 1 hour."
                except ValueError:
                    errors["overtime_hours"] = "Overtime hours must be a number."

        if request_type == "Schedule Change":
            if not new_start_time:
                errors["new_start_time"] = "Please enter the new start time."

            if not new_end_time:
                errors["new_end_time"] = "Please enter the new end time."

            if new_start_time and new_end_time:
                start_obj = datetime.strptime(new_start_time, "%H:%M").time()
                end_obj = datetime.strptime(new_end_time, "%H:%M").time()

                if end_obj <= start_obj:
                    errors["new_end_time"] = "New end time must be later than new start time."

        if not reason:
            errors["reason"] = "Please enter a reason."

        if not errors:
            StaffRequest.objects.create(
                employee_id=employee_id,
                employee_name=employee_name,
                request_type=request_type,
                assigned_schedule=assigned_schedule,
                overtime_hours=overtime_hours if request_type == "Overtime" else None,
                new_start_time=new_start_time if request_type == "Schedule Change" else None,
                new_end_time=new_end_time if request_type == "Schedule Change" else None,
                reason=reason,
                status="Pending",
            )

            messages.success(request, "Request submitted successfully.")
            return redirect("staff_requests_home")

    return render(request, "requests/staff_request_create.html", {
        "employee_id": employee_id,
        "employee_name": employee_name,
        "assigned_schedules": assigned_schedules,
        "errors": errors,
        "old": old,
    })