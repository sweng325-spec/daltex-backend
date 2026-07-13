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

    class Meta:
        model = InventoryTransactionLog
        fields = '__all__'

    def get_item_name(self, obj):
        # 🌟 Updated to handle both accessory and spare_part from your InventoryItem model
        if obj.item_type in ['accessory', 'spare_part'] and obj.inventory_item:
            # Returns the item name (e.g., "MX Master 3S Mouse" or "DDR5 16GB Laptop RAM")
            return getattr(obj.inventory_item, 'item_name', str(obj.inventory_item))
            
        elif obj.item_type == 'hardware' and obj.hardware_asset:
            return f"{obj.hardware_asset.brand} {obj.hardware_asset.model_or_pn} ({obj.hardware_asset.serial_number})"
            
        return "Unknown Item"