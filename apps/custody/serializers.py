from rest_framework import serializers
from .models import ConsumerCustody

class CustodyAssignmentLookupSerializer(serializers.ModelSerializer):
    # بيانات الموظف (ستعود قيمتها null تلقائياً إذا كانت العهدة مصروفة لمقر)
    employee_id = serializers.CharField(source='employee.employee_code', read_only=True, allow_null=True)
    employee_name_en = serializers.CharField(source='employee.name_en', read_only=True, allow_null=True)
    employee_name_ar = serializers.CharField(source='employee.name_ar', read_only=True, allow_null=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True, allow_null=True)
    
    # حقول الهيكل التنظيمي المحدثة لتعمل ديناميكياً مع الموظف أو المقر المباشر
    branch_name = serializers.SerializerMethodField()
    sector_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    structure_id = serializers.SerializerMethodField()
    
    # بيانات الأصل (Asset)
    asset_serial = serializers.CharField(source='asset.serial_number', read_only=True)
    asset_brand = serializers.CharField(source='asset.brand', read_only=True)
    asset_model = serializers.CharField(source='asset.model_or_pn', read_only=True)

    class Meta:
        model = ConsumerCustody
        fields = [
            'id', 
            'employee_id', 'employee_name_en', 'employee_name_ar', 'employee_email',
            'structure_id', 'branch_name', 'sector_name', 'department_name',
            'asset_serial', 'asset_brand', 'asset_model', 
            'assignment_date', 
            'action_type',
            'notes'
        ]

    def _get_active_structure(self, obj):
        """دالة مساعدة لجلب الهيكل الفعال سواء من الموظف أو من العهدة المكانية مباشرة"""
        if obj.employee and obj.employee.branch_structure:
            return obj.employee.branch_structure
        return obj.branch_structure

    def get_structure_id(self, obj):
        struct = self._get_active_structure(obj)
        return struct.id if struct else None

    def get_branch_name(self, obj):
        struct = self._get_active_structure(obj)
        if struct and struct.branch:
            # تم تعديل name_an إلى name_en أو الاسم المتاح للتأمين
            return getattr(struct.branch, 'name_en', None) or getattr(struct.branch, 'name', None) or str(struct.branch)
        return None

    def get_sector_name(self, obj):
        struct = self._get_active_structure(obj)
        if struct and struct.sector:
            return getattr(struct.sector, 'name_en', None) or getattr(struct.sector, 'name', None) or str(struct.sector)
        return None

    def get_department_name(self, obj):
        struct = self._get_active_structure(obj)
        if struct and struct.department:
            return getattr(struct.department, 'name_en', None) or getattr(struct.department, 'name', None) or str(struct.department)
        return None