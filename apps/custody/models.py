from django.db import models
from apps.hardware_specs.models import BaseAsset  # مسار تطبيق الأصول
from django.contrib.auth.models import User
# 🌟 استيراد موديل الهيكل الجديد، وحذف استيرادات الأقسام والقطاعات القديمة من هنا
from apps.organization.models import Branch, BranchStructure 


class Employee(models.Model):
    employee_code = models.CharField(
        max_length=50, 
        primary_key=True, 
        verbose_name="Employee Code"
    )
    name_ar = models.CharField(max_length=255, verbose_name="Name (Arabic)")
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name (English)")
    
    
    email = models.EmailField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="Email Address"
    )
    
    
    branch_structure = models.ForeignKey(
        "organization.BranchStructure", 
        on_delete=models.PROTECT,  # حماية الموظف من حذف الهيكل الإداري بالخطأ
        db_column='branch_structure_id', # ليتطابق مع اسم العمود في الـ SQL
        null=True, 
        blank=True,
        related_name='employees',
        verbose_name="Branch Structure"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'custody_employee'  # لضمان مطابقة اسم الجدول في قاعدة البيانات

    def __str__(self):
        return f"{self.employee_code} - {self.name_ar}"



class ConsumerCustody(models.Model):
    ACTION_CHOICES = [
        ('issue', 'صرف عهدة'),
        ('return', 'إرجاع للمخزن'),
    ]

    asset = models.ForeignKey(BaseAsset, on_delete=models.CASCADE, related_name='custody_history')
    
    
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE,
        blank=True, 
        null=True, 
        db_column='employee_id', 
        related_name='custodies'
    )
    
    branch_structure = models.ForeignKey(
        BranchStructure, 
        on_delete=models.PROTECT, 
        blank=True, 
        null=True, 
        related_name="structure_custodies",
        verbose_name="Assigned to Branch/Sector/Department"
    )
    
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    assignment_date = models.DateField(verbose_name="Assignment Date")
    return_date = models.DateField(blank=True, null=True, verbose_name="Return Date")
    notes = models.TextField(blank=True, null=True)
    
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 🔒 حماية برمجية (Validation): لضمان أن العهدة تذهب إما لموظف أو لهيكل إداري وليس فارغاً تماماً
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.employee and not self.branch_structure:
            raise ValidationError("You should assign any asset to Employee or branch ")
        if self.employee and self.branch_structure:
            raise ValidationError("you should assign to one of emp or branch")
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'custody_consumercustody'  

    def __str__(self):
        return f"Custody {self.asset} -> {self.employee}"