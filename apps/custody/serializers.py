from rest_framework import serializers
from .models import ConsumerCustody

class CustodyAssignmentLookupSerializer(serializers.ModelSerializer):
    # 1️⃣ جلب بيانات الموظف الأساسية ديناميكياً (باستخدام الـ employee_code كـ ID)
    employee_id = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_name_en = serializers.CharField(source='employee.name_en', read_only=True)
    employee_name_ar = serializers.CharField(source='employee.name_ar', read_only=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True) # الحقل الجديد المضاف
    
    # 2️⃣ السحر هنا: جلب المسميات الجغرافية والإدارية من خلال الـ branch_structure الجديد للموظف
    # نقوم بالغوص عبر العلاقات: employee -> branch_structure -> (branch / sector / department)
    branch_name = serializers.CharField(source='employee.branch_structure.branch.name_an', read_only=True) # عدل name_an لحقلك الفعلي
    sector_name = serializers.CharField(source='employee.branch_structure.sector.name', read_only=True)
    department_name = serializers.CharField(source='employee.branch_structure.department.name', read_only=True)
    
    # 3️⃣ جلب تفاصيل الأصل (Asset Details)
    asset_serial = serializers.CharField(source='asset.serial_number', read_only=True)
    asset_brand = serializers.CharField(source='asset.brand', read_only=True)
    asset_model = serializers.CharField(source='asset.model_or_pn', read_only=True)

    class Meta:
        model = ConsumerCustody
        fields = [
            'id', 
            'employee_id', 'employee_name_en', 'employee_name_ar', 'employee_email',
            'branch_name', 'sector_name', 'department_name', # الحقول التنظيمية المحدثة بالكامل
            'asset_serial', 'asset_brand', 'asset_model', 
            'assignment_date', 
            'action_type'
        ]