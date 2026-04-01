from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from employees.models import Employee


@require_http_methods(["GET", "POST"])
def login_view(request):
    # If already logged in, route them right away
    existing_id = request.session.get("employee_id")
    if existing_id:
        emp = Employee.objects.filter(employee_id=existing_id, is_active=True).first()
        if emp:
            return redirect("post_login")
        request.session.flush()  # clears session safely

    if request.method == "POST":
        emp_id = (request.POST.get("employee_id") or "").strip()
        password = request.POST.get("password") or ""

        emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()

        if emp and check_password(password, emp.password_hash):
            request.session["employee_id"] = emp.employee_id
            request.session["employee_role"] = emp.role  # ✅ store role for routing/navbar decisions
            request.session["employee_name"] = emp.name  # optional, handy for display later
            return redirect("post_login")

        messages.error(request, "Invalid employee ID or password.")

    return render(request, "accounts/login.html")


def post_login(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login")

    emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
    if not emp:
        request.session.flush()
        return redirect("login")

    # keep session values in sync (in case role changed)
    request.session["employee_role"] = emp.role
    request.session["employee_name"] = emp.name

    # ✅ Admin navbar pages
    if emp.role in ("Admin/Manager", "Manager"):
        return redirect("admin_employees_home")

    # ✅ Staff navbar pages
    return redirect("staff_home")


@require_http_methods(["POST", "GET"])
def logout_view(request):
    request.session.flush()  # clears everything (id/role/name)
    return redirect("login")


def staff_home(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login")

    emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
    if not emp:
        request.session.flush()
        return redirect("login")

    # Staff only (optional guard)
    if emp.role in ("Admin/Manager", "Manager"):
        return redirect("admin_employees_home")

    return render(request, "accounts/staff_home.html", {"employee": emp})