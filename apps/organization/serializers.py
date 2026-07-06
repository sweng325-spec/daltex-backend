from rest_framework import serializers
from .models import Branch, Sector, Department, BranchStructure

# ==========================================
# 🏢 BRANCH SERIALIZERS
# ==========================================
class BranchSerializer(serializers.ModelSerializer):
    """يُستخدم لعرض وإنشاء الفروع"""
    class Meta:
        model = Branch
        fields = '__all__'


# ==========================================
# 📊 SECTOR SERIALIZERS
# ==========================================
class SectorSerializer(serializers.ModelSerializer):
    """يُستخدم لعمليات الإضافة والتعديل للقطاعات (يتوقع فرع كـ ID)"""
    class Meta:
        model = Sector
        fields = '__all__'

class SectorReadSerializer(serializers.ModelSerializer):
    """يُستخدم لجلب القطاع مدمجاً معه بيانات الفرع التابع له بالكامل"""
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = Sector
        fields = '__all__'


# ==========================================
# 🗂️ DEPARTMENT SERIALIZERS
# ==========================================
class DepartmentSerializer(serializers.ModelSerializer):
    """يُستخدم لعمليات الإضافة والتعديل للإدارات (يتوقع قطاع كـ ID)"""
    class Meta:
        model = Department
        fields = '__all__'

class DepartmentReadSerializer(serializers.ModelSerializer):
    """يُستخدم لعرض تفصيلي كامل للإدارة والقطاع والفرع في الـ Frontend"""
    sector = SectorReadSerializer(read_only=True)

    class Meta:
        model = Department
        fields = '__all__'


# ==========================================
# 🌟 BRANCH STRUCTURE SERIALIZERS (الهيكل الموحد الجديد)
# ==========================================
class BranchStructureSerializer(serializers.ModelSerializer):
    """يُستخدم لعمليات الإضافة والتعديل للتوليفة الهيكلية (يتوقع IDs للفروع والقطاعات والإدارات)"""
    class Meta:
        model = BranchStructure
        fields = '__all__'

class BranchStructureReadSerializer(serializers.ModelSerializer):
    """يُستخدم لعرض شجرة الهيكل بالكامل بشكل متداخل ومفصل داخل الـ Frontend والـ الأصول"""
    branch = BranchSerializer(read_only=True)
    sector = SectorSerializer(read_only=True)
    # استخدام سيريلايزر الإدارة العادي لمنع التداخل اللانهائي للبيانات المتكررة
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = BranchStructure
        fields = '__all__'