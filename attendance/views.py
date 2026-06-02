import csv
import io
import os
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods
from django.db.utils import OperationalError

from computations.models import AttendanceSummary
from employees.models import Employee
from . import models
from .forms import CSVUploadForm


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        emp_id = request.session.get("employee_id")
        if not emp_id:
            return redirect("login")

        emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
        if not emp:
            return redirect("login")

        if emp.role not in ("Admin/Manager", "Manager"):
            return HttpResponseForbidden("Admins only.")

        request.current_employee = emp
        return view_func(request, *args, **kwargs)
    return wrapper


def _parse_dt(value: str):
    if not value:
        return None

    s = value.strip()

    dt = parse_datetime(s)
    if dt:
        return dt

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    return None


@admin_required
@require_http_methods(["GET", "POST"])
def upload_csv(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Please upload a valid CSV file.")
            return render(request, "attendance/upload.html", {"form": form})

        csv_file = form.cleaned_data["csv_file"]

        if not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Please upload a valid CSV file.")
            return render(request, "attendance/upload.html", {"form": form})

        upload_dir = os.path.join("media", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        fs = FileSystemStorage(location=upload_dir)
        saved_filename = fs.save(csv_file.name, csv_file)

        try:
            csv_file.seek(0)
            data_set = csv_file.read().decode("utf-8-sig")
        except Exception:
            messages.error(request, "Could not read the CSV file. Make sure it's UTF-8 encoded.")
            return render(request, "attendance/upload.html", {"form": form})

        io_string = io.StringIO(data_set)

        try:
            next(io_string)
        except StopIteration:
            messages.error(request, "Error: The CSV file is empty.")
            return render(request, "attendance/upload.html", {"form": form})

        success_count = 0
        error_count = 0
        skipped_duplicates = 0
        error_log = []

        for row_index, row in enumerate(csv.reader(io_string, delimiter=","), start=2):
            try:
                if len(row) < 3:
                    raise ValueError("Row has fewer than 3 columns.")

                emp_id_raw = (row[0] or "").strip()
                start_raw = (row[1] or "").strip()
                end_raw = (row[2] or "").strip()

                if not emp_id_raw:
                    raise ValueError("Missing employee_id.")

                emp_id = int(emp_id_raw)

                start_dt = _parse_dt(start_raw)
                end_dt = _parse_dt(end_raw)

                if not start_dt or not end_dt:
                    raise ValueError("Invalid date/time format.")

                if end_dt < start_dt:
                    raise ValueError("end_date_time is earlier than start_date_time.")

                if models.Attendance.objects.filter(
                    employee_id=emp_id,
                    start_date_time=start_dt,
                    end_date_time=end_dt
                ).exists():
                    skipped_duplicates += 1
                    continue

                models.Attendance.objects.create(
                    employee_id=emp_id,
                    start_date_time=start_dt,
                    end_date_time=end_dt,
                    source_system="UTAK",
                )
                success_count += 1

                duration = end_dt - start_dt
                hours_worked = duration.total_seconds() / 3600.0

                p_start = datetime(2026, 5, 16).date()
                p_end = datetime(2026, 5, 30).date()

                employee_obj = Employee.objects.get(employee_id=emp_id)

                summary, created = AttendanceSummary.objects.get_or_create(
                    employee=employee_obj,
                    payroll_period_start=p_start,
                    payroll_period_end=p_end,
                    defaults={'total_regular_hours': 0.0, 'total_overtime_hours': 0.0}
                )

                summary.total_regular_hours += float(hours_worked)
                summary.save()

            except Exception as e:
                error_count += 1
                error_log.append(f"Row {row_index}: {str(e)}")

        models.ImportHistory.objects.create(
            filename=saved_filename,
            success_count=success_count,
            error_count=error_count,
            status="Completed" if error_count == 0 else "Completed with Errors",
        )

        context = {
            "success": success_count,
            "errors": error_count,
            "duplicates": skipped_duplicates,
            "log": error_log,
        }
        return render(request, "attendance/summary.html", context)

    form = CSVUploadForm()
    return render(request, "attendance/upload.html", {"form": form})


@admin_required
@require_http_methods(["GET"])
def import_history(request):
    try:
        history = list(models.ImportHistory.objects.all().order_by("-date_uploaded"))
    except OperationalError:
        history = []

    return render(request, "attendance/history.html", {"history": history})