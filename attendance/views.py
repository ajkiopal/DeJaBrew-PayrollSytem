import csv
import io
import os
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods
from django.db.utils import OperationalError

from employees.models import Employee
from . import models


# --- Admin-only decorator (same logic as your employees app) ---
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
    """
    Tries multiple datetime formats so your demo doesn't break depending on CSV format.
    Adjust formats here if needed.
    """
    if not value:
        return None

    s = value.strip()

    # Try Django's built-in parser first (expects ISO-ish format)
    dt = parse_datetime(s)
    if dt:
        return dt

    # Try common CSV formats
    formats = [
        "%Y-%m-%d %H:%M:%S",      # 2026-02-26 08:00:00
        "%Y-%m-%d %H:%M",         # 2026-02-26 08:00
        "%m/%d/%Y %H:%M:%S",      # 02/26/2026 08:00:00
        "%m/%d/%Y %H:%M",         # 02/26/2026 08:00
        "%d/%m/%Y %H:%M:%S",      # 26/02/2026 08:00:00
        "%d/%m/%Y %H:%M",         # 26/02/2026 08:00
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    return None


#@admin_required
@require_http_methods(["GET", "POST"])
def upload_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("utak_csv")

        if not csv_file:
            messages.error(request, "No file uploaded.")
            return render(request, "attendance/upload.html")

        if not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Please upload a valid CSV file.")
            return render(request, "attendance/upload.html")

        # Ensure upload directory exists
        upload_dir = os.path.join("media", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # Save file (demo-friendly)
        fs = FileSystemStorage(location=upload_dir)
        saved_filename = fs.save(csv_file.name, csv_file)

        # Read file contents (use the uploaded file object, not the saved one)
        try:
            csv_file.seek(0)
            data_set = csv_file.read().decode("utf-8-sig")  # handles BOM too
        except Exception:
            messages.error(request, "Could not read the CSV file. Make sure it's UTF-8 encoded.")
            return render(request, "attendance/upload.html")

        io_string = io.StringIO(data_set)

        # Skip header safely
        try:
            next(io_string)
        except StopIteration:
            messages.error(request, "Error: The CSV file is empty.")
            return render(request, "attendance/upload.html")

        success_count = 0
        error_count = 0
        skipped_duplicates = 0
        error_log = []

        for row_index, row in enumerate(csv.reader(io_string, delimiter=","), start=2):
            try:
                # Expect columns: employee_id, start_date_time, end_date_time
                if len(row) < 3:
                    raise ValueError("Row has fewer than 3 columns.")

                emp_id_raw = (row[0] or "").strip()
                start_raw = (row[1] or "").strip()
                end_raw = (row[2] or "").strip()

                if not emp_id_raw:
                    raise ValueError("Missing employee_id.")

                emp_id = emp_id_raw.zfill(4)

                start_dt = _parse_dt(start_raw)
                end_dt = _parse_dt(end_raw)

                if not start_dt or not end_dt:
                    raise ValueError("Invalid date/time format.")

                # Optional sanity check
                if end_dt < start_dt:
                    raise ValueError("end_date_time is earlier than start_date_time.")

                # Duplicate check: employee_id + start_dt
                if models.Attendance.objects.filter(employee_id=emp_id, start_date_time=start_dt).exists():
                    skipped_duplicates += 1
                    continue

                models.Attendance.objects.create(
                    employee_id=emp_id,
                    start_date_time=start_dt,
                    end_date_time=end_dt,
                    source_system="UTAK",
                )
                success_count += 1

            except Exception as e:
                error_count += 1
                error_log.append(f"Row {row_index}: {str(e)}")

        models.ImportHistory.objects.create(
            filename=saved_filename,
            success_count=success_count,
            error_count=error_count,
            status="Completed",
        )

        context = {
            "success": success_count,
            "errors": error_count,
            "duplicates": skipped_duplicates,
            "log": error_log,
        }
        return render(request, "attendance/summary.html", context)

    return render(request, "attendance/upload.html")


#@admin_required
@require_http_methods(["GET"])
def import_history(request):
    try:
        history = list(models.ImportHistory.objects.all().order_by("-date_uploaded"))
    except OperationalError:
        history = []

    return render(request, "attendance/history.html", {"history": history})

# @admin_required # Uncomment this once your login is fixed!
def export_attendance_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="merged_attendance_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['EmployeeID', 'StartTime', 'EndTime'])

    attendances = models.Attendance.objects.all().order_by('start_date_time')

    for record in attendances:
        formatted_id = str(record.employee.employee_id).zfill(4)
        
        writer.writerow([
            formatted_id,
            record.start_date_time.strftime('%Y-%m-%d %H:%M:%S'),
            record.end_date_time.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response