from django.shortcuts import render, get_object_or_404
from computations.models import PayrollRecord, AttendanceSummary, AdjustmentRecord
from computations.views import admin_required, _compute_payroll
from employees.models import Employee as CoreEmployee
from decimal import Decimal

@admin_required
def admin_payslip_list(request):
    all_employees = CoreEmployee.objects.filter(is_active=True).order_by('name')
    
    records = PayrollRecord.objects.all().order_by('-payroll_period_end', 'employee__employee_id')
    
    return render(request, "payroll/admin_list.html", {
        "records": records,
        "all_employees": all_employees
    })

@admin_required
def view_payslip_detail(request, record_id):
    record = get_object_or_404(PayrollRecord, id=record_id)
    employee = record.employee
    
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
    return render(request, "payroll/payslip_template.html", context)