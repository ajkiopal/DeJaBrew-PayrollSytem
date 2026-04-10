from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from employees.models import Employee


@require_http_methods(["GET", "POST"])
def login_view(request):
    existing_id = request.session.get("employee_id")
    if existing_id:
        emp = Employee.objects.filter(employee_id=existing_id, is_active=True).first()
        if emp:
            return redirect("post_login")
        request.session.flush()

    if request.method == "POST":
        emp_id = (request.POST.get("employee_id") or "").strip()
        password = request.POST.get("password") or ""

        emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()

        if emp and check_password(password, emp.password_hash):
            request.session["employee_id"] = emp.employee_id
            request.session["employee_role"] = emp.role
            request.session["employee_name"] = emp.name
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

    request.session["employee_role"] = emp.role
    request.session["employee_name"] = emp.name

    # First-time password setup only
    if emp.must_change_password:
        return redirect("set_first_password")

    # Only Admin goes to admin dashboard
    if emp.role == "Admin/Manager":
        return redirect("admin_employees_home")

    # Manager + Staff go to staff dashboard
    return redirect("staff_home")


@require_http_methods(["GET", "POST"])
def set_first_password(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login")

    emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
    if not emp:
        request.session.flush()
        return redirect("login")

    if not emp.must_change_password:
        return redirect("post_login")

    if request.method == "POST":
        new_password = (request.POST.get("new_password") or "").strip()
        confirm_password = (request.POST.get("confirm_password") or "").strip()

        if not new_password or not confirm_password:
            messages.error(request, "Please fill in both password fields.")
            return render(request, "accounts/set_first_password.html", {"employee": emp})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/set_first_password.html", {"employee": emp})

        if new_password == "00000":
            messages.error(request, "Your new password cannot be the default password.")
            return render(request, "accounts/set_first_password.html", {"employee": emp})

        emp.password_hash = make_password(new_password)
        emp.must_change_password = False
        emp.save()

        messages.success(request, "Password set successfully.")
        return redirect("post_login")

    return render(request, "accounts/set_first_password.html", {"employee": emp})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    request.session.flush()
    return redirect("login")


def staff_home(request):
    emp_id = request.session.get("employee_id")
    if not emp_id:
        return redirect("login")

    emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
    if not emp:
        request.session.flush()
        return redirect("login")

    if emp.must_change_password:
        return redirect("set_first_password")

    # Admin should not use staff dashboard
    if emp.role == "Admin/Manager":
        return redirect("admin_employees_home")

    # You said to replace accounts/staff_home.html with templates/base_staff.html
    return render(request, "base_staff.html", {"employee": emp})