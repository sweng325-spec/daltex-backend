from rest_framework import serializers
from .models import BaseAsset, ComputerAsset, PrinterAsset, TabletAsset, MonitorAsset

# 1️⃣ الـ Serializers الخاصة بالموديلات المورثة (Polymorphic Specs)
class ComputerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputerAsset
        fields = '__all__'

class PrinterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrinterAsset
        fields = '__all__'

class TabletSerializer(serializers.ModelSerializer):
    class Meta:
        model = TabletAsset
        fields = '__all__'

class MonitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorAsset
        fields = '__all__'


# 2️⃣ الـ Serializer الرئيسي للأصل الأساسي
class BaseAssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_en', read_only=True)

    class Meta:
        model = BaseAsset
        fields = '__all__'

    def validate_serial_number(self, value):
        """ضمان أن السيريال نمبر فريد، وحفظه دائماً بالحروف الكبيرة (Uppercase)"""
        # 🛠️ تصحيح: إزالة toUpperCase() الخاصة بـ JavaScript واستخدام ميثود بايثون النظيفة .upper()
        normalized = value.strip().upper()
        
        instance_id = self.instance.id if self.instance else None
        if BaseAsset.objects.filter(serial_number=normalized).exclude(id=instance_id).exists():
            raise serializers.ValidationError("A device with this serial number already exists.")
        return normalized


# 3️⃣ الـ Serializer المجمع والمسطح لعرض الجدول بالكامل في الـ React
class BaseAssetFlatSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_en', read_only=True)
    current_custody = serializers.SerializerMethodField()
    specs = serializers.SerializerMethodField()

    class Meta:
        model = BaseAsset
        fields = [
            'id', 'serial_number', 'brand', 'model_or_pn', 'status', 
            'description', 'category_name', 'current_custody', 'specs'
        ]

    def get_current_custody(self, obj):
        """
        جلب بيانات العهدة النشطة الحالية فقط وسحب بيانات الموظف
        وموقعه الجغرافي من خلال الـ branch_structure الجديد بأمان.
        """
        latest_custody = obj.custody_history.filter(
            action_type='issue', 
            return_date__isnull=True
        ).order_by('-assignment_date', '-id').first()
        
        if latest_custody and latest_custody.employee:
            emp = latest_custody.employee
            
            # 🌟 الغوص الذكي والأمن عبر الهيكل الإداري الجديد الموحد
            branch_name = None
            sector_name = None
            department_name = None
            
            if emp.branch_structure:
                struct = emp.branch_structure
                # جلب اسم الفرع (مع fallback لـ name_an التابع لجدول الفروع لديك)
                if struct.branch:
                    branch_name = getattr(struct.branch, 'name_an', None) or getattr(struct.branch, 'name', None) or str(struct.branch)
                
                # جلب اسم القطاع
                if struct.sector:
                    sector_name = getattr(struct.sector, 'name', None) or str(struct.sector)
                
                # جلب اسم الإدارة
                if struct.department:
                    department_name = getattr(struct.department, 'name', None) or str(struct.department)

            return {
                "employee_code": emp.employee_code,
                "employee_name_ar": emp.name_ar,
                "employee_name_en": emp.name_en,
                "employee_email": emp.email, # إرجاع الإيميل الجديد أيضاً للفرونت إند
                "branch_name": branch_name,
                "sector_name": sector_name,
                "department_name": department_name,
                "assignment_date": latest_custody.assignment_date
            }
        return None

    def get_specs(self, obj):
        """تحديد نوع الموديل المورث ديناميكياً وإرجاع مواصفاته التقنية الخاصة"""
        if hasattr(obj, 'computerasset'):
            return ComputerSerializer(obj.computerasset).data
        elif hasattr(obj, 'printerasset'):
            return PrinterSerializer(obj.printerasset).data
        elif hasattr(obj, 'tabletasset'):
            return TabletSerializer(obj.tabletasset).data
        elif hasattr(obj, 'monitorasset'):
            return MonitorSerializer(obj.monitorasset).data
        return None