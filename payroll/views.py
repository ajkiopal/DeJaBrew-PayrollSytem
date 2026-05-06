from django.shortcuts import render, get_object_or_404
from computations.models import PayrollRecord, AttendanceSummary, AdjustmentRecord
from computations.views import admin_required, _compute_payroll
from employees.models import Employee as CoreEmployee
from decimal import Decimal

@admin_required
def admin_payslip_list(request):
    target_run_id = request.GET.get('run_id')
    all_employees = CoreEmployee.objects.filter(is_active=True).order_by('name')
    
    records = PayrollRecord.objects.all().order_by('-payroll_period_end', 'employee__employee_id')
    
    if target_run_id:
        records = records.filter(payroll_run_id=target_run_id)
    
    return render(request, "payroll/admin_list.html", {
        "records": records,
        "all_employees": all_employees
    })

def view_payslip_detail(request, record_id):
    record = get_object_or_404(PayrollRecord, id=record_id)
    employee = record.employee
    
    user_role = request.session.get('role')
    session_emp_id = request.session.get('employee_id')

    summary = AttendanceSummary.objects.filter(
        employee=employee, 
        payroll_period_start=record.payroll_period_start
    ).first()
    
    computed = _compute_payroll(employee, summary)

    context = {
        "employee": employee,
        "record": record,
        "payroll": {
            **computed,
            "total_hours": summary.total_regular_hours if summary else 0,
            "net_pay": record.net_pay,
            "total_gov_deductions": computed['total_gov_deductions']
        }
    }
    if user_role == 'Admin':
        return render(request, "payroll/payslip_template.html", context)
    else:
        return render(request, "payroll/staff_payslip_template.html", context)
    return render(request, "payroll/payslip_template.html", context)

def staff_payslip_list(request):
    # Get the ID from the session[cite: 1]
    emp_id = request.session.get("employee_id")
    
    if not emp_id:
        return redirect("login")

    # Filter records where the employee ID matches the session[cite: 3]
    # 'records' is what the template expects
    records = PayrollRecord.objects.filter(
        employee__employee_id=emp_id
    ).order_by("-payroll_period_end")

    return render(request, "payroll/staff_list.html", {
        "records": records
    })