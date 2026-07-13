from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from django.db.models import ProtectedError

from .models import BaseAsset, ComputerAsset, PrinterAsset, TabletAsset, MonitorAsset, AssetCategory
from .serializers import (
    BaseAssetSerializer, 
    BaseAssetFlatSerializer,
    ComputerSerializer, 
    PrinterSerializer, 
    TabletSerializer, 
    MonitorSerializer
)

# =====================================================================
# 1. عمليات الأصول الرئيسية (Hardware Assets CRUD)
# =====================================================================

@api_view(['GET', 'POST'])
def hardware_asset_list(request):
    if request.method == 'GET':
        # 🚀 Query Optimization لضمان الأداء السريع جداً مع جلب الهيكل الجديد للموظف المستلم
        assets = BaseAsset.objects.select_related(
            'category'
        ).select_related(
            'computerasset', 'printerasset', 'tabletasset', 'monitorasset'
        ).prefetch_related(
            'custody_history__employee__branch_structure__branch',
            'custody_history__employee__branch_structure__sector',
            'custody_history__employee__branch_structure__department'
        ).order_by('-id')
        
        serializer = BaseAssetFlatSerializer(assets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = BaseAssetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def maintenance_assets_by_category(request):
    """
    API view to return all hardware assets with status='maintenance',
    filtered dynamically by an English category name query parameter.
    """
    category_param = request.query_params.get('category')

    if not category_param:
        return Response(
            {'error': 'The "category" query parameter is required. Example: ?category=computer'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 1. 🚀 Query Optimization
    queryset = BaseAsset.objects.filter(status='maintenance').select_related(
        'category', 'computerasset', 'printerasset', 'tabletasset', 'monitorasset'
    ).prefetch_related(
        'custody_history__employee__branch_structure__branch',
        'custody_history__employee__branch_structure__sector',
        'custody_history__employee__branch_structure__department'
    )

    # 2. 🔍 FIXED LOOKUP: Targeting 'name_en' using double underscores
    queryset = queryset.filter(category__name_en__iexact=category_param).order_by('-id')

    # 3. Serialize and return
    serializer = BaseAssetFlatSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def hardware_asset_instock_count(request):
    """
    Returns the total number of hardware assets that are currently 'in_stock'.
    """
    # Assuming your model field is named 'status'. Change 'in_stock' if your choice value differs.
    instock_count = BaseAsset.objects.filter(status='in_stock').count()
    
    return Response(
        {
            "status": "success",
            "in_stock_count": instock_count
        }, 
        status=status.HTTP_200_OK
    )

@api_view(['GET', 'PUT', 'DELETE'])
def hardware_asset_detail(request, pk):
    try:
        asset = BaseAsset.objects.get(pk=pk)
    except BaseAsset.DoesNotExist:
        return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = BaseAssetFlatSerializer(asset)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = BaseAssetSerializer(asset, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        asset.delete()
        return Response({'message': 'Asset deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# 2. عمليات الطابعات (Printers CRUD)
# =====================================================================

@api_view(['GET', 'POST'])
def printer_list(request):
    if request.method == 'GET':
        printers = PrinterAsset.objects.all().order_by('-baseasset_ptr_id')
        serializer = PrinterSerializer(printers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        serializer = PrinterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def printer_detail(request, pk):
    try:
        printer = PrinterAsset.objects.get(baseasset_ptr_id=pk)
    except PrinterAsset.DoesNotExist:
        return Response({'error': 'Printer specs not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PrinterSerializer(printer)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'PUT':
        serializer = PrinterSerializer(printer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    elif request.method == 'DELETE':
        printer.delete()
        return Response({'message': 'Printer specs deleted'}, status=status.HTTP_204_NO_CONTENT)
    
    
# =====================================================================
# 3. عمليات الأجهزة (Computers CRUD)
# =====================================================================  
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from apps.hardware_specs.models import AssetCategory
from .models import ComputerAsset
from .serializers import ComputerSerializer

@api_view(['GET', 'POST'])
def computer_list(request):
    if request.method == 'GET':
        computers = ComputerAsset.objects.all().order_by('-baseasset_ptr_id')
        serializer = ComputerSerializer(computers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
        # Create a mutable copy of request data so we can modify it
        data = request.data.copy()
        
        # Automatically assign the category if it wasn't provided in the body
        if not data.get('category'):
            try:
                # Adjust the lookup filter ('name', 'name_en', or 'slug') based on your AssetCategory fields
                category_obj, created = AssetCategory.objects.get_or_create(
                    name_en="Computer", 
                    defaults={"name_ar": "أجهزة كمبيوتر"}
                )
                data['category'] = category_obj.id
            except Exception as e:
                return Response(
                    {"error": f"Failed to automatically resolve 'Computer' AssetCategory: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Pass the modified data dictionary into your serializer
        serializer = ComputerSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def computer_detail(request, pk):
    try:
        computer = ComputerAsset.objects.get(baseasset_ptr_id=pk)
    except ComputerAsset.DoesNotExist:
        return Response({'error': 'Computer asset not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ComputerSerializer(computer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = ComputerSerializer(computer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        computer.delete()
        return Response({'message': 'Computer asset deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    

@api_view(['GET'])
def computer_list_by_type(request, pc_type):
    clean_type = pc_type.lower()
    if clean_type not in ['desktop', 'laptop']:
        return Response(
            {'error': f"Invalid PC type '{pc_type}'. Choose 'desktop' or 'laptop'."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    computers = ComputerAsset.objects.filter(pc_type__iexact=clean_type).order_by('-baseasset_ptr_id')
    serializer = ComputerSerializer(computers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# =====================================================================
# 4. عمليات الأجهزة اللوحية (Tablets CRUD)
# =====================================================================

@api_view(['GET', 'POST'])
def tablet_list(request):
    if request.method == 'GET':
        tablets = TabletAsset.objects.all().order_by('-baseasset_ptr_id')
        serializer = TabletSerializer(tablets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
        serializer = TabletSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def tablet_detail(request, pk):
    try:
        tablet = TabletAsset.objects.get(baseasset_ptr_id=pk)
    except TabletAsset.DoesNotExist:
        return Response({'error': 'Tablet asset not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = TabletSerializer(tablet)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = TabletSerializer(tablet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        tablet.delete()
        return Response({'message': 'Tablet asset deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# 5. التقارير والجرد (Inventory Stock Report)
# =====================================================================

@api_view(['GET'])
def inventory_stock_report_fast(request):
    categories_data = AssetCategory.objects.annotate(
        quantity_in_stock=Count('assets', filter=Q(assets__status='in_stock')),
        quantity_assigned=Count('assets', filter=Q(assets__status='assigned'))
    ).values('id', 'name_ar', 'name_en', 'code', 'quantity_in_stock', 'quantity_assigned')

    report = list(categories_data)
    for item in report:
        item['total_registered'] = item['quantity_in_stock'] + item['quantity_assigned']

    return Response(report, status=status.HTTP_200_OK)


# =====================================================================
# 6. عمليات التصنيفات المنفصلة (Categories Split CRUD)
# =====================================================================

@api_view(['GET'])
def get_all_categories(request):
    """جلب كافة التصنيفات الموجودة في النظام بدون استثناء"""
    categories = AssetCategory.objects.all().order_by('id')
    data = [
        {
            "id": cat.id,
            "name_ar": cat.name_ar,
            "name_en": cat.name_en,
            "category_type": cat.category_type
        } for cat in categories
    ]
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_spare_parts_categories(request):
    """جلب تصنيفات قطع الغيار والاكسسوارات فقط (Spare Parts)"""
    categories = AssetCategory.objects.filter(category_type='accessory').order_by('id')
    data = [
        {
            "id": cat.id,
            "name_ar": cat.name_ar,
            "name_en": cat.name_en,
            "category_type": cat.category_type
        } for cat in categories
    ]
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_base_asset_categories(request):
    categories = AssetCategory.objects.filter(category_type='base_asset').order_by('id')
    data = [
        {
            "id": cat.id,
            "name_ar": cat.name_ar,
            "name_en": cat.name_en,
            "category_type": cat.category_type
        } for cat in categories
    ]
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_accessory_categories(request):
    categories = AssetCategory.objects.filter(category_type='accessory').order_by('id')
    data = [
        {
            "id": cat.id,
            "name_ar": cat.name_ar,
            "name_en": cat.name_en,
            "category_type": cat.category_type
        } for cat in categories
    ]
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
def post_new_category(request):
    name_en = request.data.get('name_en')
    name_ar = request.data.get('name_ar')
    category_type = request.data.get('category_type', 'base_asset')

    if not name_en:
        return Response({"error": "The field 'name_en' is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Updated to support all dynamic tracking inventory choices
    valid_types = ['computer', 'spare_part', 'accessory', 'base_asset']
    if category_type not in valid_types:
        return Response(
            {"error": f"Invalid category_type. Choose from: {valid_types}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if a category with this English name and type already exists to prevent duplicates
    if AssetCategory.objects.filter(name_en__iexact=name_en, category_type=category_type).exists():
        return Response(
            {"error": f"A category with name '{name_en}' and type '{category_type}' already exists."},
            status=status.HTTP_400_BAD_REQUEST
        )

    category = AssetCategory.objects.create(
        name_en=name_en,
        name_ar=name_ar,
        category_type=category_type
    )

    return Response({
        "message": "Category created successfully.",
        "category": {
            "id": category.id,
            "name_en": category.name_en,
            "name_ar": category.name_ar,
            "category_type": category.category_type
        }
    }, status=status.HTTP_201_CREATED)
    
    
@api_view(['DELETE'])
def delete_category(request, pk):
    try:
        category = AssetCategory.objects.get(id=pk)
        category.delete()
        return Response({"message": f"Category '{category.name_en}' deleted successfully."}, status=status.HTTP_200_OK)
        
    except AssetCategory.DoesNotExist:
        return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        
    except ProtectedError:
        return Response(
            {"error": "Cannot delete this category because active items are assigned to it."},
            status=status.HTTP_400_BAD_REQUEST
        )


# =====================================================================
# 7. عمليات الشاشات (Monitors CRUD) - الأسماء الأصلية تماماً
# =====================================================================

@api_view(['GET', 'POST'])
def monitor_list_create(request):
    if request.method == 'GET':
        monitors = MonitorAsset.objects.all().order_by('-baseasset_ptr_id')
        serializer = MonitorSerializer(monitors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = MonitorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def monitor_detail_update_delete(request, pk):
    try:
        monitor = MonitorAsset.objects.get(baseasset_ptr_id=pk)
    except MonitorAsset.DoesNotExist:
        try:
            monitor = MonitorAsset.objects.get(id=pk)
        except MonitorAsset.DoesNotExist:
            return Response(
                {"error": f"Monitor with ID {pk} does not exist in the system."}, 
                status=status.HTTP_404_NOT_FOUND
            )

    if request.method == 'GET':
        serializer = MonitorSerializer(monitor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = MonitorSerializer(monitor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PATCH':
        serializer = MonitorSerializer(monitor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        monitor.delete()
        return Response({"message": "Monitor asset successfully deleted."}, status=status.HTTP_200_OK)
    
    
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
def get_in_stock_assets_by_category(request):
    
    category_name = request.query_params.get('category', None)
    
    if not category_name:
        return Response(
            {"error": "Please provide a 'category' parameter in the URL (e.g., ?category=pc)"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        
        assets = BaseAsset.objects.select_related(
            'category', 
            'computerasset'
        ).filter(
            status='in_stock'
        ).filter(
            Q(category__name_en__icontains=category_name) | 
            Q(category__name_ar__icontains=category_name)
        ).order_by('-id')

        data = []
        for asset in assets:
            cat = asset.category
            
            
            asset_data = {
                "id": asset.id,
                "serial_number": getattr(asset, 'serial_number', None),
                "brand": getattr(asset, 'brand', None),
                "model_or_pn": getattr(asset, 'model_or_pn', None),
                "status": asset.status,
                "category": {
                    "id": cat.id if cat else None,
                    "name_en": cat.name_en if cat else None,
                    "name_ar": cat.name_ar if cat else None,
                }
            }

           
            if cat and cat.name_en.lower() in ['computer', 'pc', 'laptop']:
                
                comp_specs = getattr(asset, 'computerasset', None)
                
                if comp_specs:
                    asset_data["specs"] = {
                        "processor": getattr(comp_specs, 'processor', None),
                        "ram": getattr(comp_specs, 'ram', None),
                        "storage": getattr(comp_specs, 'storage', None),
                        "os": getattr(comp_specs, 'os', None),
                        
                    }
                else:
                    asset_data["specs"] = "No hardware specs recorded for this computer"

            data.append(asset_data)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )