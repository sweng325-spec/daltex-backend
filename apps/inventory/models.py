from django.db import models
from apps.hardware_specs.models import AssetCategory  # ربط المخزن بنفس جدول التصنيفات
from apps.organization.models import Branch


class InventoryItem(models.Model):
    """
    جدول مخزن الملحقات والمستهلكات العامة التي تقاس بالأعداد والكميات المتاحة داخل الفروع.
    (مثل: الأحبار، الشنط الاحتياطية، الكابلات، لوحات المفاتيح والماوس غير المعينة كأصول).
    """
    
    UNIT_CHOICES = [
        ('pcs', 'Piece (حبة/قطعة)'),
        ('box', 'Box (علبة/صندوق)'),
        ('meter', 'Meter (متر)'),
        ('pack', 'Pack (عبوة)'),
    ]

    # ربط القطعة بالتصنيف العام (مثال: حبر يتبع تصنيف Printers، أو شنطة تتبع تصنيف Computers)
    category = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, related_name="inventory_items"
    )

    item_name = models.CharField(
        max_length=255,
        verbose_name="Item Name (e.g., HP 963X Ink / Backpack Bag)",
    )
    brand = models.CharField(max_length=100, blank=True, null=True)
    part_number = models.CharField(max_length=150, blank=True, null=True)

    # فرع المستودع الحالي المتواجد به الأرصدة
    stored_in_branch = models.ForeignKey(
        "organization.Branch", on_delete=models.PROTECT, related_name="inventory_stock_items"
    )

    # التحكم بالأرقام والكميات المتاحة في الأرصدة المخزنية غير المصروفة لمستهلك
    quantity_in_stock = models.PositiveIntegerField(
        default=0, verbose_name="Available Quantity in Stock"
    )
    minimum_required_qty = models.PositiveIntegerField(
        default=5, verbose_name="Minimum Limit for Low Stock Alerts"
    )
    
    # وحدة قياس الكمية
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs', verbose_name="Unit of Measurement")
    
    # مكان التخزين داخل الغرفة أو المخزن (لراحة الدعم الفني)
    storage_location = models.CharField(max_length=150, blank=True, null=True, verbose_name="Storage Rack / Location")

    # الموديلات المتوافقة مع هذا الملحق لسهولة الصرف والبحث للدعم الفني
    compatible_with_model = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Compatible with Hardware Models",
    )

    description = models.TextField(blank=True, null=True, verbose_name="Notes / Specifications")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_accessories_stock"
        verbose_name = "Inventory Accessory"
        verbose_name_plural = "Inventory Accessories"
        
        # 🔒 حماية: لمنع تكرار نفس العنصر بنفس الـ Part Number في نفس الفرع (تحديث الكميات بدلاً من تكرار السطور)
        unique_together = ('part_number', 'stored_in_branch', 'item_name')

    def __str__(self):
        return f"{self.item_name} ({self.quantity_in_stock} {self.get_unit_display()}) at {self.stored_in_branch.name_en}"

    @property
    def is_low_stock(self):
        """تنبيه فوري لو قارب المخزون على النفاذ لطلب شراء أحبار أو مستلزمات"""
        return self.quantity_in_stock <= self.minimum_required_qty
    
    
from django.db import models
from django.contrib.auth.models import User
from .models import InventoryItem
from apps.hardware_specs.models import BaseAsset

class InventoryTransactionLog(models.Model):
    ACTION_CHOICES = [
        ('addition', 'New Item Registered (إضافة صنف جديد)'),
        ('increase', 'Stock Increase / Inbound (زيادة رصيد)'),
        ('decrease', 'Stock Decrease / Outbound (صرف رصيد)'),
        ('delete', 'Record Deleted (حذف صنف)'),
    ]

    ITEM_TYPE_CHOICES = [
        ('accessory', 'Accessory / Consumable'),
        ('hardware', 'Hardware Asset'),
    ]

    # Who performed the operation
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_actions"
    )
    
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    
    # Flexible linkages (null since a log can be for either an accessory or hardware asset)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    hardware_asset = models.ForeignKey(BaseAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_logs")
    
    # For quantities
    quantity_changed = models.IntegerField(default=0, verbose_name="Quantity Delta (+/-)")
    new_total_quantity = models.PositiveIntegerField(default=0, verbose_name="Resulting Stock Balance")
    
    notes = models.TextField(blank=True, null=True, verbose_name="Reason / Transaction Details")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_transaction_logs"
        ordering = ['-created_at']

    def __str__(self):
        item_name = self.inventory_item.item_name if self.inventory_item else self.hardware_asset.serial_number
        return f"{self.action_type} by {self.user} on {item_name}"