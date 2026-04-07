from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import EmployeeCreateForm, EmployeeEditForm
from .models import Employee


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        # TEMPORARY BYPASS (REMOVE AFTER TESTING)
        return view_func(request, *args, **kwargs)

        emp_id = request.session.get("employee_id")
        # if not emp_id:
        #     return redirect("login")

        emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
        # if not emp:
        #     request.session.flush()
        #     return redirect("login")

        # if emp.must_change_password:
        #     return redirect("set_first_password")

        # Only Admin/Manager can access admin pages
        # if emp.role != "Admin/Manager":
        #     return HttpResponseForbidden("Admins only.")

        request.current_employee = emp
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_required(view_func):
    def wrapper(request, *args, **kwargs):
        # TEMPORARY BYPASS (REMOVE AFTER TESTING)
        return view_func(request, *args, **kwargs)

        emp_id = request.session.get("employee_id")
        # if not emp_id:
        #     return redirect("login")

        emp = Employee.objects.filter(employee_id=emp_id, is_active=True).first()
        # if not emp:
        #     request.session.flush()
        #     return redirect("login")

        # if emp.must_change_password:
        #     return redirect("set_first_password")

        request.current_employee = emp
        return view_func(request, *args, **kwargs)
    return wrapper


@employee_required
def employee_home(request):
    emp = request.current_employee

    if emp.role == "Admin/Manager":
        return redirect("admin_employees_home")

    return render(request, "base_staff.html", {"employee": emp})


@admin_required
@require_http_methods(["GET", "POST"])
def admin_employees_home(request):
    mode = request.GET.get("mode", "none")
    edit_id = request.GET.get("id")

    add_form = EmployeeCreateForm()
    edit_form = None
    editing_emp = None
    show_add_validation = False
    show_edit_validation = False

    if mode == "edit" and edit_id:
        editing_emp = get_object_or_404(Employee, employee_id=edit_id)
        edit_form = EmployeeEditForm(instance=editing_emp)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            mode = "add"
            add_form = EmployeeCreateForm(request.POST)

            if add_form.is_valid():
                cleaned = add_form.cleaned_data

                duplicate_exists = Employee.objects.filter(
                    name=cleaned["name"],
                    contact_number=cleaned["contact_number"],
                ).exists()

                if duplicate_exists:
                    add_form.add_error(None, "This employee record already exists.")
                    show_add_validation = True
                else:
                    emp = add_form.save(commit=False)
                    emp.password_hash = make_password("00000")
                    emp.must_change_password = True
                    emp.save()

                    messages.success(request, "Employee successfully added.")
                    return redirect("admin_employees_home")
            else:
                show_add_validation = True

        elif action == "save":
            mode = "edit"
            emp_id = request.POST.get("employee_id")

            if not emp_id:
                show_edit_validation = True
            else:
                editing_emp = get_object_or_404(Employee, employee_id=emp_id)
                edit_form = EmployeeEditForm(request.POST, instance=editing_emp)

                if edit_form.is_valid():
                    edit_form.save()
                    messages.success(request, "Employee information updated successfully.")
                    return redirect("admin_employees_home")
                else:
                    show_edit_validation = True

        elif action == "delete":
            emp_id = request.POST.get("employee_id")

            if emp_id:
                Employee.objects.filter(employee_id=emp_id).delete()
                messages.success(request, "Employee deleted successfully.")
                return redirect("admin_employees_home")

    employees = list(Employee.objects.all().order_by("employee_id"))
    empty_message = "No employees added yet." if len(employees) == 0 else ""

    return render(request, "employees/employees_home.html", {
        "employees": employees,
        "empty_message": empty_message,
        "mode": mode,
        "add_form": add_form,
        "edit_form": edit_form,
        "editing_emp": editing_emp,
        "show_add_validation": show_add_validation,
        "show_edit_validation": show_edit_validation,
    })


@admin_required
@require_http_methods(["POST"])
def employee_reset_password(request, employee_id):
    emp = get_object_or_404(Employee, employee_id=employee_id)

    emp.password_hash = make_password("00000")
    emp.must_change_password = True
    emp.save()

    messages.success(request, f"Password for {emp.name} has been reset to the temporary default password.")
    messages.success(request, "The employee will be required to set a new password on next login.")
    return redirect("admin_employees_home")

employees_home = admin_employees_home