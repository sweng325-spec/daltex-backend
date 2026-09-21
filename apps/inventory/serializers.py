from rest_framework import serializers
from .models import InventoryItem, InventoryTransactionLog

class InventoryAccessoriesStockSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_en', read_only=True)
    branch_name = serializers.CharField(source='stored_in_branch.name_en', read_only=True)

    class Meta:
        model = InventoryItem
        fields = '__all__'


class InventoryTransactionLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    item_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryTransactionLog
        fields = '__all__'

    def get_item_name(self, obj):
        # 1. Handle Accessories & Spare Parts
        if obj.item_type in ['accessory', 'spare_part'] and obj.inventory_item:
            return getattr(obj.inventory_item, 'item_name', str(obj.inventory_item))
            
        # 2. Handle Hardware / Asset logs
        elif obj.item_type in ['asset', 'hardware']:
            if obj.hardware_asset:
                brand = getattr(obj.hardware_asset, 'brand', '') or ''
                model = getattr(obj.hardware_asset, 'model_or_pn', getattr(obj.hardware_asset, 'model', '')) or ''
                serial = getattr(obj.hardware_asset, 'serial_number', str(obj.hardware_asset))
                
                if brand or model:
                    return f"{brand} {model} ({serial})".strip()
                return str(serial)
            
            elif getattr(obj, 'hardware_asset_id', None):
                return f"Asset ({obj.hardware_asset_id})"

        return "Unknown Item"

    def get_category_name(self, obj):
        """
        Retrieves category name (e.g., Computer, Printer, Keyboard, Mouse) 
        from related InventoryItem or BaseAsset category.
        """
        # Accessory / Consumable Category
        if obj.inventory_item and hasattr(obj.inventory_item, 'category') and obj.inventory_item.category:
            return getattr(obj.inventory_item.category, 'name_en', str(obj.inventory_item.category))

        # Hardware Asset Category
        if obj.hardware_asset and hasattr(obj.hardware_asset, 'category') and obj.hardware_asset.category:
            return getattr(obj.hardware_asset.category, 'name_en', str(obj.hardware_asset.category))

        return "Uncategorized"