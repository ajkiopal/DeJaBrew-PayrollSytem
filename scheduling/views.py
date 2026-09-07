from datetime import datetime, timedelta

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from employees.models import Employee
from employees.views import admin_required, employee_required
from .models import ScheduleEvent


def today_date():
    return datetime.today().date()


def view_start_date():
    return today_date() - timedelta(days=183)


def view_end_date():
    return today_date() + timedelta(days=183)


def post_start_date():
    return today_date()


def post_end_date():
    return today_date() + timedelta(days=183)


def parse_time_input(value):
    value = value.strip()

    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None


def render_admin_schedule(request, employees, field_errors=None, form_values=None, show_add_modal=False):
    return render(request, "scheduling/admin_schedule_home.html", {
        "employees": employees,
        "today": post_start_date().isoformat(),
        "max_post_date": post_end_date().isoformat(),
        "field_errors": field_errors or {},
        "form_values": form_values or {},
        "show_add_modal": show_add_modal,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def admin_schedule_home(request):
    employees = Employee.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        field_errors = {}
        form_values = {
            "title": request.POST.get("title", "").strip(),
            "date": request.POST.get("date", "").strip(),
            "start_time": request.POST.get("start_time", "").strip(),
            "end_time": request.POST.get("end_time", "").strip(),
            "description": request.POST.get("description", "").strip(),
            "assigned_employees": request.POST.getlist("assigned_employees"),
        }

        assigned_employee_ids = [emp_id for emp_id in form_values["assigned_employees"] if emp_id]

        if not form_values["title"]:
            field_errors["title"] = "Shift title is required."

        if not form_values["date"]:
            field_errors["date"] = "Date is required."

        if not form_values["start_time"]:
            field_errors["start_time"] = "Start time is required."

        if not form_values["end_time"]:
            field_errors["end_time"] = "End time is required."

        if not assigned_employee_ids:
            field_errors["assigned_employees"] = "Please assign at least one employee."

        if len(assigned_employee_ids) != len(set(assigned_employee_ids)):
            field_errors["assigned_employees"] = "The same employee cannot be assigned more than once."

        shift_date = None
        if form_values["date"]:
            try:
                shift_date = datetime.strptime(form_values["date"], "%Y-%m-%d").date()
            except ValueError:
                field_errors["date"] = "Invalid date."

        start_time = parse_time_input(form_values["start_time"]) if form_values["start_time"] else None
        end_time = parse_time_input(form_values["end_time"]) if form_values["end_time"] else None

        if form_values["start_time"] and not start_time:
            field_errors["start_time"] = "Use HH:MM format, for example 09:30."

        if form_values["end_time"] and not end_time:
            field_errors["end_time"] = "Use HH:MM format, for example 17:30."

        if shift_date:
            if shift_date < post_start_date():
                field_errors["date"] = "You cannot post schedules for dates that have already passed."

            if shift_date > post_end_date():
                field_errors["date"] = "Schedules can only be posted within the six-month reference period."

        if start_time and end_time and end_time <= start_time:
            field_errors["end_time"] = "End time must be later than start time."

        if not field_errors:
            overlapping_shift = ScheduleEvent.objects.filter(
                status="Posted",
                date=shift_date,
                assigned_employees__employee_id__in=assigned_employee_ids,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).distinct().first()

            if overlapping_shift:
                overlapping_names = overlapping_shift.assigned_employees.filter(
                    employee_id__in=assigned_employee_ids
                ).values_list("name", flat=True)

                names_text = ", ".join(overlapping_names)
                field_errors["assigned_employees"] = f"{names_text} already has an overlapping posted shift."

        if field_errors:
            return render_admin_schedule(
                request,
                employees,
                field_errors=field_errors,
                form_values=form_values,
                show_add_modal=True,
            )

        event = ScheduleEvent.objects.create(
            title=form_values["title"],
            date=shift_date,
            start_time=start_time,
            end_time=end_time,
            description=form_values["description"],
            status="Posted",
        )

        event.assigned_employees.set(assigned_employee_ids)

        messages.success(request, "Shift schedule posted successfully.")
        return redirect("admin_schedule_home")

    return render_admin_schedule(request, employees)


@employee_required
def staff_schedule_home(request):
    return render(request, "scheduling/staff_schedule_home.html")


@employee_required
def schedule_events(request):
    events = ScheduleEvent.objects.filter(
        status="Posted",
        date__gte=view_start_date(),
        date__lte=view_end_date(),
    ).order_by("date", "start_time")

    data = []

    for event in events:
        start_datetime = datetime.combine(event.date, event.start_time)
        end_datetime = datetime.combine(event.date, event.end_time)

        employee_names = ", ".join([
            emp.name for emp in event.assigned_employees.all()
        ])

        display_title = event.title
        if employee_names:
            display_title = f"{event.title} - {employee_names}"

        data.append({
            "id": event.id,
            "title": display_title,
            "start": start_datetime.isoformat(),
            "end": end_datetime.isoformat(),
            "extendedProps": {
                "schedule_title": event.title,
                "date": event.date.strftime("%B %d, %Y"),
                "start_time": event.start_time.strftime("%I:%M %p"),
                "end_time": event.end_time.strftime("%I:%M %p"),
                "assigned_employees": employee_names if employee_names else "No employees assigned",
                "description": event.description if event.description else "No description provided",
                "status": event.status,
                "unpost_url": f"/schedule/unpost/{event.id}/",
            }
        })

    return JsonResponse(data, safe=False)


@admin_required
@require_http_methods(["POST"])
def unpost_schedule_event(request, event_id):
    event = get_object_or_404(
        ScheduleEvent,
        id=event_id,
        date__gte=view_start_date(),
        date__lte=view_end_date(),
    )

    event.status = "Unposted"
    event.save()

    messages.success(request, "Shift schedule unposted successfully.")
    return redirect("admin_schedule_home")