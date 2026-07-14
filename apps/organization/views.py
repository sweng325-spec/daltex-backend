from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Branch, Sector, Department, BranchStructure
from .serializers import (
    BranchSerializer, 
    SectorSerializer, 
    SectorReadSerializer,
    DepartmentSerializer, 
    DepartmentReadSerializer,
    BranchStructureSerializer,
    BranchStructureReadSerializer
)

# ==========================================
# 🏢 BRANCHES CRUD
# ==========================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def branch_list(request):
    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_branch'):
            return Response(
                {"error": "You do not have permission to view the branches list."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        branches = Branch.objects.all().order_by('branch_id')
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.add_branch'):
            return Response(
                {"error": "You do not have permission to add a branch."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BranchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_branch(request, branch_id):
    """
    API view to update a Branch name or properties by its branch_id.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('organization.change_branch'):
        return Response(
            {"error": "You do not have permission to update branches."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        branch = Branch.objects.get(branch_id=branch_id)
        
        name_en = request.data.get('name_en')
        name_ar = request.data.get('name_ar')

        if not any([name_en, name_ar]) and request.method == 'PUT':
            return Response(
                {"error": "No valid naming parameters provided for update."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if name_en is not None:
            branch.name_en = name_en
            
        if name_ar is not None:
            branch.name_ar = name_ar

        branch.save()

        return Response({
            "message": f"Branch with ID {branch_id} updated successfully.",
            "branch": {
                "branch_id": branch.branch_id,
                "name_en": branch.name_en,
                "name_ar": branch.name_ar
            }
        }, status=status.HTTP_200_OK)

    except Branch.DoesNotExist:
        return Response(
            {"error": f"Branch with ID {branch_id} not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def branch_detail(request, pk):
    try:
        branch = Branch.objects.get(pk=pk)
    except Branch.DoesNotExist:
        return Response({'error': 'Branch not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_branch'):
            return Response(
                {"error": "You do not have permission to view this branch's details."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BranchSerializer(branch)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.change_branch'):
            return Response(
                {"error": "You do not have permission to update this branch."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BranchSerializer(branch, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.delete_branch'):
            return Response(
                {"error": "You do not have permission to delete this branch."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        branch.delete()
        return Response({'message': 'Branch deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


# ==========================================
# 📊 SECTORS CRUD
# ==========================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sector_list(request):
    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_sector'):
            return Response(
                {"error": "You do not have permission to view the sectors list."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        sectors = Sector.objects.all().order_by('sector_id')
        serializer = SectorReadSerializer(sectors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # 🔒 Authorization Check: يتطلب صلاحية إضافة قطاع وربطه بالفرع
        if not request.user.has_perm('organization.add_sector'):
            return Response(
                {"error": "You do not have permission to add a sector."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        if not request.user.has_perm('organization.add_branchstructure'):
            return Response(
                {"error": "You do not have permission to create structural links for this sector."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SectorSerializer(data=request.data)
        if serializer.is_valid():
            # 1. حفظ القطاع الجديد أولاً في جدول sectors
            sector = serializer.save()
            
            # 2. استقبال بيانات الربط المرسلة من الفرونت إند (React)
            branch_id = request.data.get('branch_id')
            department_id = request.data.get('department_id') # اختياري أو إلزامي حسب تصميمك
            
            # 3. التحقق من إرسال فرع على الأقل لإنشاء علاقة الهيكل التنظيمي
            if branch_id:
                try:
                    BranchStructure.objects.create(
                        branch_id=branch_id,
                        sector=sector,
                        department_id=department_id # سينزل كـ NULL في قاعدة البيانات إذا لم يُرسل
                    )
                except Exception as e:
                    # في حال حدوث خطأ أثناء إنشاء الربط (مثل عدم وجود الـ id في قاعدة البيانات)
                    return Response(
                        {"error": f"Sector created, but failed to link with branch: {str(e)}"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Serializer Errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sectors_by_branch(request, branch_id):
    """جلب كافة القطاعات التابعة لفرع معين بناءً على الـ branch_id عبر الجدول المركزي"""
    # 🔒 Authorization Check
    if not request.user.has_perm('organization.view_sector'):
        return Response(
            {"error": "You do not have permission to view filtered sectors."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # نقوم بالفلترة من خلال العلاقة العكسية لجدول الهيكل التنظيمي الموحد
    sectors = Sector.objects.filter(structures__branch_id=branch_id).distinct()
    
    serializer = SectorSerializer(sectors, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def sector_detail(request, pk):
    try:
        sector = Sector.objects.get(pk=pk)
    except Sector.DoesNotExist:
        return Response({'error': 'Sector not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_sector'):
            return Response(
                {"error": "You do not have permission to view this sector's details."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SectorReadSerializer(sector)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.change_sector'):
            return Response(
                {"error": "You do not have permission to update this sector."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SectorSerializer(sector, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # 🔒 Authorization Check: عملية الحذف هنا تمسح الربط الهيكلي للقطاع
        if not request.user.has_perm('organization.delete_branchstructure'):
            return Response(
                {"error": "You do not have permission to remove sector structural links."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 📥 Extract the specific branch from query parameters
        branch_id = request.query_params.get('branch_id')

        if not branch_id:
            return Response(
                {'error': 'branch_id query parameter is required to remove this sector from a specific branch.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔍 Find all structural records tying this sector and all its departments to this specific branch
        linked_structures = BranchStructure.objects.filter(
            branch_id=branch_id,
            sector=sector
        )

        if not linked_structures.exists():
            return Response(
                {'error': 'No structural links found matching this specific combination of Branch and Sector.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ✂️ Count how many mapping rows (departments links) are being removed for reporting
        deleted_count = linked_structures.count()

        # Wipe out all rows matching this branch + sector combination
        linked_structures.delete()
        
        return Response(
            {
                'message': f'Successfully removed this sector and its {deleted_count-1} linked department(s) from the specified branch. The global sector master data remains intact.'
            }, 
            status=status.HTTP_200_OK
        )


# ==========================================
# 🗂️ DEPARTMENTS CRUD (Centralized Structure)
# ==========================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def department_list(request, branch_id, sector_id):
    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_department'):
            return Response(
                {"error": "You do not have permission to view the departments list."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        structures = BranchStructure.objects.filter(
            branch_id=branch_id, 
            sector_id=sector_id
        ).select_related('department')
        
        departments = list({struct.department for struct in structures if struct.department})
        departments.sort(key=lambda x: x.id)
        
        serializer = DepartmentReadSerializer(departments, many=True) 
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # 🔒 Authorization Check: إضافة إدارة وربطها بالهيكل
        if not request.user.has_perm('organization.add_department'):
            return Response(
                {"error": "You do not have permission to add a department."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        if not request.user.has_perm('organization.add_branchstructure'):
            return Response(
                {"error": "You do not have permission to create structural links for this department."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            department = serializer.save()
            
            try:
                BranchStructure.objects.create(
                    branch_id=branch_id,
                    sector_id=sector_id,
                    department=department
                )
            except Exception as e:
                return Response(
                    {"error": f"Department created, but failed to link: {str(e)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            full_data_serializer = DepartmentReadSerializer(department)
            return Response(full_data_serializer.data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def departments_by_sector(request, branch_id, sector_id):
    """جلب كافة الإدارات التابعة لقطاع معين داخل فرع محدد عبر الجدول المركزي"""
    # 🔒 Authorization Check
    if not request.user.has_perm('organization.view_department'):
        return Response(
            {"error": "You do not have permission to view filtered departments."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # 1. الفلترة بالفرع والقطاع معاً داخل جدول الهيكل الموحد
    structures = BranchStructure.objects.filter(
        branch_id=branch_id, 
        sector_id=sector_id
    ).select_related('department')
    
    # 2. استخراج الأقسام الفريدة فقط واستبعاد أي قيم فارغة (Null)
    departments = list({struct.department for struct in structures if struct.department})
    
    # 3. ترتيب الأقسام هجائياً أو حسب الـ ID لضمان ثبات النتيجة في الفرونت إند
    departments.sort(key=lambda x: x.id)
    
    serializer = DepartmentSerializer(departments, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def department_detail(request, pk):
    try:
        department = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

    # 🔹 GET Method: Fetch master department details
    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_department'):
            return Response(
                {"error": "You do not have permission to view this department's details."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DepartmentReadSerializer(department)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # 🔹 PUT Method: Update master department details
    elif request.method == 'PUT':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.change_department'):
            return Response(
                {"error": "You do not have permission to update this department."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # 🔹 DELETE Method: Remove structural mapping only
    elif request.method == 'DELETE':
        # 🔒 Authorization Check: يتم هنا حذف الربط الهيكلي للإدارة وليس الإدارة الرئيسية
        if not request.user.has_perm('organization.delete_branchstructure'):
            return Response(
                {"error": "You do not have permission to remove department structural links."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Safely extract ?branch_id=X&sector_id=Y from the URL
        branch_id = request.query_params.get('branch_id')
        sector_id = request.query_params.get('sector_id')

        # Validation: Ensure query parameters aren't missing
        if not branch_id or not sector_id:
            return Response(
                {'error': 'Both branch_id and sector_id query parameters are required to remove this structural link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Look up the specific structure mapping row
        structure_record = BranchStructure.objects.filter(
            branch_id=branch_id,
            sector_id=sector_id,
            department=department
        ).first()

        if not structure_record:
            return Response(
                {'error': 'No branch structure link found matching this specific combination of Branch, Sector, and Department.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the mapping record, leaving the master Department intact
        structure_record.delete()
        
        return Response(
            {'message': 'The specific branch structure link for this department was deleted successfully.'}, 
            status=status.HTTP_200_OK
        )


# =====================================================================
# 🌟 BRANCH STRUCTURE CRUD (الهيكل المشترك الموحد)
# =====================================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def branch_structure_list(request):
    """جلب أو إنشاء توليفات الهيكل الإداري الموحد"""
    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_branchstructure'):
            return Response(
                {"error": "You do not have permission to view the branch structures list."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        structures = BranchStructure.objects.select_related('branch', 'sector', 'department').all().order_by('id')
        serializer = BranchStructureReadSerializer(structures, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'POST':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.add_branchstructure'):
            return Response(
                {"error": "You do not have permission to create a branch structure combination."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BranchStructureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def branch_structure_detail(request, pk):
    """إدارة توليفة هيكلية معينة"""
    try:
        structure = BranchStructure.objects.get(pk=pk)
    except BranchStructure.DoesNotExist:
        return Response({'error': 'Branch Structure combination not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.view_branchstructure'):
            return Response(
                {"error": "You do not have permission to view this branch structure's details."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BranchStructureReadSerializer(structure)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    elif request.method == 'PUT':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.change_branchstructure'):
            return Response(
                {"error": "You do not have permission to update this branch structure."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BranchStructureSerializer(structure, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    elif request.method == 'DELETE':
        # 🔒 Authorization Check
        if not request.user.has_perm('organization.delete_branchstructure'):
            return Response(
                {"error": "You do not have permission to delete this branch structure."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        structure.delete()
        return Response(
            {'message': 'Branch and its structures deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )