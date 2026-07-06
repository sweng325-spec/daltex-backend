from rest_framework import serializers
from .models import InventoryItem

class InventoryAccessoriesStockSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_en', read_only=True)
    branch_name = serializers.CharField(source='stored_in_branch.name_en', read_only=True)

    class Meta:
        model = InventoryItem
        fields = '__all__'
        
        
        
from rest_framework import serializers
from .models import InventoryTransactionLog

class InventoryTransactionLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    item_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryTransactionLog
        fields = '__all__'

    def get_item_name(self, obj):
        if obj.item_type == 'accessory' and obj.inventory_item:
            return obj.inventory_item.item_name
        elif obj.item_type == 'hardware' and obj.hardware_asset:
            return f"{obj.hardware_asset.brand} {obj.hardware_asset.model_or_pn} ({obj.hardware_asset.serial_number})"
        return "Unknown Item"