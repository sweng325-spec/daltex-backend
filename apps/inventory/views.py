from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import InventoryItem, InventoryTransactionLog
from .serializers import InventoryAccessoriesStockSerializer, InventoryTransactionLogSerializer
from apps.hardware_specs.models import BaseAsset  # Importing your hardware model

# =====================================================================
# 1. عمليات مخزن الإكسسوارات والجرد العام
# =====================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def inventory_list_create(request):
    """
    GET: Returns all accessories stock AND all hardware assets marked 'in_stock'.
    POST: Creates a new accessory stock entry.
    """
    if request.method == 'GET':
        # 🔒 Authorization Check: يجب أن يمتلك صلاحية عرض المخزن وعرض الأصول
        if not request.user.has_perm('inventory.view_inventoryitem'):
            return Response(
                {"error": "You do not have permission to view inventory items."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        if not request.user.has_perm('hardware_specs.view_baseasset'):
            return Response(
                {"error": "You do not have permission to view hardware assets."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 1. Fetch accessory inventory records
        accessories = InventoryItem.objects.all().order_by('id')
        acc_serializer = InventoryAccessoriesStockSerializer(accessories, many=True)
        
        # 2. Fetch all unique hardware base assets that are currently 'in_stock'
        in_stock_hardware = BaseAsset.objects.filter(status='in_stock').order_by('id')
        
        # Map fields manually to keep the footprint light and clean
        hardware_data = [
            {
                "id": asset.id,
                "serial_number": asset.serial_number,
                "brand": asset.brand,
                "model_or_pn": asset.model_or_pn,
                "status": asset.status,
                "category_name": getattr(asset.category, 'name_en', None) if asset.category else None
            }
            for asset in in_stock_hardware
        ]
        
        # 3. Return combined response payload structure
        return Response({
            "accessories_stock": acc_serializer.data,
            "available_in_stock_hardware": hardware_data
        }, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        # 🔒 Authorization Check
        if not request.user.has_perm('inventory.add_inventoryitem'):
            return Response(
                {"error": "You do not have permission to add items to the inventory."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InventoryAccessoriesStockSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def inventory_detail_update_delete(request, pk):
    """
    Handles GET, Full/Partial Updates, and Deletion for an accessory entry by ID.
    """
    try:
        item = InventoryItem.objects.get(id=pk)
    except InventoryItem.DoesNotExist:
        return Response({"error": "Inventory item not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('inventory.view_inventoryitem'):
            return Response(
                {"error": "You do not have permission to view this inventory item."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InventoryAccessoriesStockSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        # 🔒 Authorization Check
        if not request.user.has_perm('inventory.change_inventoryitem'):
            return Response(
                {"error": "You do not have permission to update this inventory item."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        partial = (request.method == 'PATCH')
        
        # Fix context issue for unique constraints validations during PATCH
        serializer = InventoryAccessoriesStockSerializer(
            item, 
            data=request.data, 
            partial=partial,
            context={'request': request} 
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Debug helper: This will print the exact validation error in your terminal shell
        print("SERIALIZER VALIDATION ERRORS:", serializer.errors)
        
        # Returns the detailed dictionary error to Postman instead of a blank object
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # 🔒 Authorization Check
        if not request.user.has_perm('inventory.delete_inventoryitem'):
            return Response(
                {"error": "You do not have permission to delete this inventory item."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        item.delete()
        return Response({"message": "Inventory stock record deleted successfully."}, status=status.HTTP_200_OK) 


# =====================================================================
# 2. تعديل كميات المخزن وتسجيل العمليات (Transactions)
# =====================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensures request.user is captured
def create_accessory_item(request):  # save to history log
    """
    Creates a new accessory item and logs the creation action.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('inventory.add_inventoryitem'):
        return Response(
            {"error": "You do not have permission to create an inventory item."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = InventoryAccessoriesStockSerializer(data=request.data)
    if serializer.is_valid():
        item = serializer.save()
        
        # Create Log entry for Addition
        InventoryTransactionLog.objects.create(
            user=request.user,
            action_type='addition',
            item_type='accessory',
            inventory_item=item,
            quantity_changed=item.quantity_in_stock,
            new_total_quantity=item.quantity_in_stock,
            notes=request.data.get('notes', 'Initial stock registration.')
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def adjust_accessory_stock(request, pk):
    """
    Endpoint to explicitly increase or decrease an accessory's stock quantity.
    Expected Payload: {"action": "increase"/"decrease", "quantity": 5, "notes": "Reason"}
    """
    # 🔒 Authorization Check: تعديل الكميات يتطلب صلاحية التعديل على موديل المخزن
    if not request.user.has_perm('inventory.change_inventoryitem'):
        return Response(
            {"error": "You do not have permission to adjust stock quantities."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        item = InventoryItem.objects.get(id=pk)
    except InventoryItem.DoesNotExist:
        return Response({"error": "Inventory item not found."}, status=status.HTTP_404_NOT_FOUND)
        
    action = request.data.get('action')
    qty = int(request.data.get('quantity', 0))
    notes = request.data.get('notes', '')

    if action not in ['increase', 'decrease'] or qty <= 0:
        return Response({"error": "Invalid action or quantity value."}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'decrease':
        if item.quantity_in_stock < qty:
            return Response({"error": "Insufficient stock balance for this request."}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity_in_stock -= qty
        delta = -qty
    else:
        item.quantity_in_stock += qty
        delta = qty

    item.save()

    # Create Log entry for the adjustment
    log = InventoryTransactionLog.objects.create(
        user=request.user if request.user.is_authenticated else None, # Safe fallback
        action_type=action,
        item_type='accessory',
        inventory_item=item,
        quantity_changed=delta,
        new_total_quantity=item.quantity_in_stock,
        notes=notes
    )

    return Response({
        "message": f"Stock successfully updated. New balance: {item.quantity_in_stock}",
        "current_stock": item.quantity_in_stock,
        "log_id": log.id
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_history_list(request):
    """
    API view to get the complete audit log history of inventory movements.
    """
    # 🔒 Authorization Check: فحص صلاحية قراءة سجلات العمليات
    if not request.user.has_perm('inventory.view_inventorytransactionlog'):
        return Response(
            {"error": "You do not have permission to view inventory transaction history."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    logs = InventoryTransactionLog.objects.select_related('user', 'inventory_item', 'hardware_asset').all().order_by('-created_at')
    serializer = InventoryTransactionLogSerializer(logs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)