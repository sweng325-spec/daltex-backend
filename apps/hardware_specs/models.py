from django.db import models
from django.contrib.auth.models import User
# 🌟 تم إزالة الاستيرادات الخاصة بـ Branch, Department, Sector لأن الأصول لم تعد ترتبط بها مباشرة

class AssetCategory(models.Model):
    """
    جدول تصنيفات الأجهزة - ديناميكي بالكامل لتتمكن من إضافة
    (أجهزة بصمة، طابعات كاشير، سيرفرات) من الـ Admin مباشرة.
    """
    name_en = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Category Name (EN) e.g., Computer, Printer, Handheld",
    )
    name_ar = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="اسم التصنيف (بالعربي) مثل: حواسب، طابعات",
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name="رمز اختياري للتصنيف (e.g., PC, PRN)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    CATEGORY_TYPE_CHOICES = [
        ('accessory', 'Accessory (Cables, Mice, Keyboard, etc.)'),
        ('base_asset', 'Base Asset (Computers, Monitors, Printers, etc.)'),
        ('spare_parts', 'Spare Parts (Replacement Components, etc.)'),
    ]
    
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPE_CHOICES,
        default='base_asset',
        verbose_name="Category Type"
    )
    
    class Meta:
        db_table = "asset_categories"
        verbose_name = "Asset Category"
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return f"{self.name_en} / {self.name_ar}"


class BaseAsset(models.Model):
    
    STATUS_CHOICES = [
        ("in_stock", "In Inventory / Stock (بالمخزن وغير معين لمستهلك)"),
        ("assigned", "Assigned to Consumer (صُرف كعهدة لموظف أو موقع)"),
        ("maintenance", "In Maintenance (في الصيانة)"),
        ("scrapped", "Scrapped / Disposed (مكهن)"),
    ]

    category = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, related_name="assets"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_stock"
    )

    
    brand = models.CharField(max_length=100, db_index=True)
    model_or_pn = models.CharField(
        max_length=150, blank=True, null=True, verbose_name="Model / Part No."
    )
    serial_number = models.CharField(max_length=100, unique=True, db_index=True)

    description = models.TextField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hardware_assets"
        indexes = [
            models.Index(fields=['status', 'category']),
        ]
        
    def __str__(self):
        return f"[{self.category.name_en}] {self.brand} - S/N: {self.serial_number} ({self.get_status_display()})"



class ComputerAsset(BaseAsset):
    """مواصفات الحواسب الشاملة بالإضافة إلى الملحقات الشخصية وحقائب الظهر التابعة لها مباشرة"""

    COMPUTER_TYPES = [("laptop", "Laptop"), ("desktop", "Desktop")]
    pc_type = models.CharField(
        max_length=10, choices=COMPUTER_TYPES, default="laptop"
    )
    processor = models.CharField(max_length=150, blank=True, null=True)
    memory_ram = models.CharField(max_length=50, blank=True, null=True)
    hard_disk = models.CharField(max_length=100, blank=True, null=True)

    monitor_brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Attached Monitor Brand")
    monitor_model = models.CharField(max_length=150, blank=True, null=True, verbose_name="Attached Monitor Model/PN")
    monitor_inches = models.CharField(max_length=50, blank=True, null=True, verbose_name="Attached Monitor Size (Inches)")
    monitor_serial = models.CharField(max_length=150, blank=True, null=True, verbose_name="Attached Monitor S/N")

    keyboard_brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Keyboard Brand")
    keyboard_model = models.CharField(max_length=150, blank=True, null=True, verbose_name="Keyboard Model/PN")
    keyboard_serial = models.CharField(max_length=150, blank=True, null=True, verbose_name="Keyboard S/N")

    mouse_brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mouse Brand")
    mouse_model = models.CharField(max_length=150, blank=True, null=True, verbose_name="Mouse Model/PN")
    mouse_serial = models.CharField(max_length=150, blank=True, null=True, verbose_name="Mouse S/N")

    bag_brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bag Brand")
    bag_model_or_description = models.CharField(max_length=255, blank=True, null=True, verbose_name="Bag Model / Description")

    class Meta:
        db_table = "asset_computers"


class PrinterAsset(BaseAsset):
    

    multifunctions = models.CharField(max_length=100, blank=True, null=True, verbose_name="Multifunctions (e.g., All In One)")
    printer_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Printer Type (e.g., Color/Mono)")
    printer_color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Printer Body Color")
    connection_type = models.CharField(max_length=150, blank=True, null=True, verbose_name="Supported Connections (e.g., Ethernet-WiFi-USB)")
    technology = models.CharField(max_length=100, blank=True, null=True, verbose_name="Technology (e.g., Inkjet/Laser)")
    
    cartridge_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cartridge Number (e.g., HP 963X)")
    cartridge_color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Cartridge Color Type")
    ink_details = models.TextField(blank=True, null=True, verbose_name="Ink Details (e.g., 4 ink_Black/Cyan...)")
    
    active_connection = models.CharField(max_length=50, blank=True, null=True, verbose_name="Active Connection (e.g., USB/Ethernet)")
    mac_address_eth = models.CharField(max_length=50, blank=True, null=True, verbose_name="MAC Address (Ethernet)")
    ip_address_eth = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address (Ethernet)")
    mac_address_wifi = models.CharField(max_length=50, blank=True, null=True, verbose_name="MAC Address (WiFi)")

    class Meta:
        db_table = "asset_printers"
        verbose_name = "Printer Asset"
        verbose_name_plural = "Printer Assets"


class MonitorAsset(BaseAsset):

    part_number = models.CharField(max_length=150, blank=True, null=True, verbose_name="Part No.")
    inches = models.CharField(max_length=50, verbose_name="Screen Size (Inches)")
    location_details = models.CharField(max_length=255, blank=True, null=True, verbose_name="Location (الموقع داخل الفرع)")
    color = models.CharField(max_length=50, blank=True, null=True, verbose_name="Color")

    is_meeting_room_tv = models.BooleanField(
        default=False, verbose_name="Is Greater than 70 inch / Meeting Room TV"
    )
    is_curved = models.BooleanField(default=False, verbose_name="Is Curved Screen")

    class Meta:
        db_table = "asset_monitors"
        verbose_name = "Monitor / TV Asset"
        verbose_name_plural = "Monitor / TV Assets"

    def save(self, *args, **kwargs):
        try:
            clean_inches = ''.join(filter(str.isdigit, str(self.inches)))
            if clean_inches and int(clean_inches) >= 70:
                self.is_meeting_room_tv = True
            else:
                self.is_meeting_room_tv = False
        except ValueError:
            pass
            
        super().save(*args, **kwargs)


class NetworkDeviceAsset(BaseAsset):
    device_type = models.CharField(
        max_length=100, verbose_name="Switch / Router / AP"
    )
    ports_count = models.IntegerField(blank=True, null=True)
    mac_address = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = "asset_network_devices"
        

class TabletAsset(BaseAsset):
    
    device_item_type = models.CharField(max_length=50, verbose_name="Item Type (e.g., Tablet/Ipad)")
    storage_ram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Storage & RAM Specs")
    screen_color_specs = models.CharField(max_length=150, blank=True, null=True, verbose_name="Color & Screen Specs")

    class Meta:
        db_table = "asset_tablets"
        verbose_name = "Tablet / iPad Asset"
        verbose_name_plural = "Tablet / iPad Assets"