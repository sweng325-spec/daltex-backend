from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Cast
from django.db.models import IntegerField
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.inventory.models import InventoryTransactionLog
from apps.organization.models import BranchStructure
from apps.hardware_specs.models import BaseAsset
from .models import ConsumerCustody
from .serializers import CustodyAssignmentLookupSerializer
from apps.custody.models import Employee
###########################################################
## Custody Management API Views
###########################################################
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_new_employee(request):
    try:

        # 🔒 Authorization Check
        if not request.user.has_perm('custody.add_employee'):
            return Response(
                {"error": "You do not have permission to register a new employee."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # ... (rest of your add_new_employee code remains exactly the same) ...
        emp_code = request.data.get('employee_code')
        name_ar = request.data.get('employee_name_ar')
        name_en = request.data.get('employee_name_en')
        email = request.data.get('email')
        
        branch_id = request.data.get('branch_id')
        sector_id = request.data.get('sector_id')
        department_id = request.data.get('department_id')
        branch_structure_id = request.data.get('branch_structure_id')
        print("emp_code",emp_code)
        print("name_ar",name_ar)
        if not emp_code or not name_ar:
            return Response({"error": "employee_code and employee_name_ar are required fields."}, status=status.HTTP_400_BAD_REQUEST)

        if Employee.objects.filter(employee_code=emp_code).exists():
            return Response({"error": f"Employee with code '{emp_code}' already exists."}, status=status.HTTP_400_BAD_REQUEST)

        structure_obj = None
        if branch_structure_id:
            try:
                structure_obj = BranchStructure.objects.get(id=branch_structure_id)
            except BranchStructure.DoesNotExist:
                return Response({"error": "Selected branch_structure_id does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        elif branch_id and department_id:
            lookup_filters = {'branch_id': branch_id, 'department_id': department_id}
            if sector_id:
                lookup_filters['sector_id'] = sector_id
            structure_obj, created = BranchStructure.objects.get_or_create(**lookup_filters)

        new_emp = Employee.objects.create(
            employee_code=emp_code,
            name_ar=name_ar,
            name_en=name_en if name_en else "",
            email=email,
            branch_structure=structure_obj
        )

        return Response({"message": "Employee recorded successfully.", "employee_code": new_emp.employee_code}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.pagination import PageNumberPagination
    
class EmployeePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unique_employee_list(request):
    """
    Paginated, searchable, and filterable endpoint for employee management.
    """
    if not request.user.has_perm('custody.view_employee'):
        return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    try:
        # 1. Base Queryset
        queryset = Employee.objects.select_related(
            'branch_structure__branch',
            'branch_structure__sector',
            'branch_structure__department'
        ).all()

        # 2. Inactive Employee Filter (Default: Active only unless checkbox checked)
        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
        # if not include_inactive:
        #     queryset = queryset.filter(status='active')

        # 3. Dropdown Filtering
        branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
        sector_id = request.query_params.get('sector_id') or request.query_params.get('sector')
        dept_id = request.query_params.get('department_id') or request.query_params.get('department')
        status_filter = request.query_params.get('status')    

        if branch_id and branch_id.strip():
            queryset = queryset.filter(branch_structure__branch_id=branch_id.strip())
        if sector_id and sector_id.strip():
            queryset = queryset.filter(branch_structure__sector_id=sector_id.strip())
        if dept_id and dept_id.strip():
            queryset = queryset.filter(branch_structure__department_id=dept_id.strip())

        if status_filter and status_filter.strip():
            status_list = [s.strip() for s in status_filter.split(',')]
            queryset = queryset.filter(status__in=status_list)



        # 4. Search Filter (Code, Name, Email)
        search_query = request.query_params.get('search')
        if search_query and search_query.strip():
            term = search_query.strip()
            queryset = queryset.filter(
                Q(employee_code__icontains=term) |
                Q(name_ar__icontains=term) |
                Q(name_en__icontains=term) |
                Q(email__icontains=term)
            )

        queryset = queryset.order_by('employee_code')

        # 5. Export All Resolution (Unpaginated)
        export_all = request.query_params.get('all', 'false').lower() == 'true'
        if export_all:
            data = [build_employee_dict(emp) for emp in queryset]
            return Response(data, status=status.HTTP_200_OK)

        # 6. Paginated Response
        paginator = EmployeePagination()
        page = paginator.paginate_queryset(queryset, request)
        
        data = [build_employee_dict(emp) for emp in page]
        return paginator.get_paginated_response(data)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def build_employee_dict(emp):
    struct = emp.branch_structure
    return {
        "employee_code": emp.employee_code,
        "employee_name_ar": emp.name_ar,
        "employee_name_en": emp.name_en,
        "email": emp.email,
        "status": emp.status,
        "last_known_branch": getattr(struct.branch, 'name_en', getattr(struct.branch, 'name', None)) if struct and struct.branch else None,
        "last_known_branch_id": struct.branch_id if struct else None,
        "last_known_sector": getattr(struct.sector, 'sector_name', getattr(struct.sector, 'name', None)) if struct and struct.sector else None,
        "last_known_sector_id": struct.sector_id if struct else None,
        "last_known_department": getattr(struct.department, 'name', None) if struct and struct.department else None,
        "last_known_department_id": struct.department_id if struct else None,
    }
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_employee_by_code(request, employee_code):
    """
    API view to retrieve a single employee's profile by their unique employee_code.
    Safely handles dynamic branch, department, and status naming fields.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.view_employee'):
        return Response(
            {"error": "You do not have permission to view employee details."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # استخدام select_related لجلب العلاقات المبطنة من جدول الربط المركزي الموحد
        employee = Employee.objects.select_related(
            'branch_structure__branch', 
            'branch_structure__department'
        ).get(employee_code=employee_code)
        
        # استخراج الهيكل التنظيمي المربوط بالموظف
        struct = employee.branch_structure
        
        # 🛡️ Safe Extraction for Branch Name (عبر الـ branch_structure)
        branch_name = None
        if struct and struct.branch:
            branch_name = (
                getattr(struct.branch, 'branch_name', None) or 
                getattr(struct.branch, 'name_en', None) or 
                getattr(struct.branch, 'name', None) or 
                str(struct.branch)
            )
        
        sector_name = None
        if struct and struct.sector:
            sector_name = (
                getattr(struct.sector, 'sector_name', None) or 
                getattr(struct.branch, 'name_en', None) or 
                getattr(struct.branch, 'name', None) or 
                str(struct.branch)
            )
        # 🛡️ Safe Extraction for Department Name (عبر الـ branch_structure)
        department_name = None
        if struct and struct.department:
            department_name = (
                getattr(struct.department, 'department_name', None) or 
                getattr(struct.department, 'name_en', None) or 
                getattr(struct.department, 'name', None) or 
                str(struct.department)
            )

        return Response({
            "employee_code": employee.employee_code,
            "employee_name_ar": employee.name_ar,
            "employee_name_en": employee.name_en,
            "email": employee.email,
            "status": employee.status,  # 🌟 تم إضافة حقل الحالة في الملف الشخصي للموظف هنا
            "last_known_branch": branch_name,
            "last_known_sector": sector_name,
            "last_known_department": department_name,
            "created_at": employee.created_at,
            "updated_at": employee.updated_at
        }, status=status.HTTP_200_OK)
        
    except Employee.DoesNotExist:
        return Response(
            {"error": f"Employee with code '{employee_code}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_employee(request, employee_code):
    """
    API view to safely delete an employee by their unique code.
    Blocks deletion if the employee holds active asset custody.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.delete_employee'):
        return Response(
            {"error": "You do not have permission to delete an employee."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        employee = Employee.objects.get(employee_code=employee_code)
        
        # Safety Check: Verify if employee has any unreturned asset custodies
        active_custody_exists = ConsumerCustody.objects.filter(
            employee=employee, 
            action_type='issue', 
            return_date__isnull=True
        ).exists()
        
        if active_custody_exists:
            return Response(
                {"error": f"Cannot delete employee {employee_code}. They currently hold active asset custody items that must be returned first."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Safe to delete if no active custody tracks exist
        employee.delete()
        return Response(
            {"message": f"Employee with code {employee_code} has been successfully removed from the system."},
            status=status.HTTP_200_OK
        )
        
    except Employee.DoesNotExist:
        return Response(
            {"error": f"Employee with code {employee_code} not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_employee(request, employee_code):
    if not request.user.has_perm('custody.change_employee'):
        return Response(
            {"error": "You do not have permission to update employee details."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        employee = Employee.objects.select_related('branch_structure').get(employee_code=employee_code)
        
        # 1. Update Name fields
        if 'name_ar' in request.data or 'nameAr' in request.data:
            employee.name_ar = request.data.get('name_ar') or request.data.get('nameAr', '')
            
        if 'name_en' in request.data or 'nameEn' in request.data:
            employee.name_en = request.data.get('name_en') or request.data.get('nameEn', '')

        # 2. Update Email & Status
        if 'email' in request.data:
            employee.email = request.data['email']
            
        if 'status' in request.data:
            employee.status = request.data['status']
            
        # 3. Branch / Sector / Department Structure Resolution
        structure_id = request.data.get('structure_id') or request.data.get('structureId')
        
        # Option A: Exact structure_id provided
        if structure_id:
            try:
                employee.branch_structure = BranchStructure.objects.get(id=structure_id)
            except BranchStructure.DoesNotExist:
                return Response({"error": f"Structure {structure_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        # Option B: Individual branch_id, sector_id, or department_id provided
        elif any(k in request.data for k in ['branch_id', 'sector_id', 'department_id', 'branchId', 'sectorId', 'departmentId']):
            current_struct = employee.branch_structure
            
            # Merge incoming data with current existing structure fallbacks
            branch_id = request.data.get('branch_id') or request.data.get('branchId') or (current_struct.branch_id if current_struct else None)
            sector_id = request.data.get('sector_id') or request.data.get('sectorId') or (current_struct.sector_id if current_struct else None)
            department_id = request.data.get('department_id') or request.data.get('departmentId') or (current_struct.department_id if current_struct else None)

            # Build query filter
            lookup_filters = {}
            if branch_id:
                lookup_filters['branch_id'] = branch_id
            if department_id:
                lookup_filters['department_id'] = department_id
            if sector_id:
                lookup_filters['sector_id'] = sector_id

            target_structure = BranchStructure.objects.filter(**lookup_filters).first()
            
            if not target_structure:
                return Response(
                    {"error": "No matching Branch/Sector/Department structure combination found."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            employee.branch_structure = target_structure

        employee.save()
        
        # Return populated details
        struct = employee.branch_structure
        return Response({
            "message": "Employee updated successfully.",
            "employee": {
                "employee_code": employee.employee_code,
                "name_ar": employee.name_ar,
                "name_en": employee.name_en,
                "email": employee.email,
                "status": employee.status,
                "structure_id": struct.id if struct else None,
                "branch_id": struct.branch_id if struct else None,
                "sector_id": struct.sector_id if struct else None,
                "department_id": struct.department_id if struct else None,
            }
        }, status=status.HTTP_200_OK)

    except Employee.DoesNotExist:
        return Response({"error": f"Employee {employee_code} not found."}, status=status.HTTP_404_NOT_FOUND)

############################################################################
## Asset Assignment API Views
############################################################################
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_asset_custody(request):
    """
    API view to issue an in-stock asset to an employee using their unique code.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.add_consumercustody'):
        return Response(
            {"error": "You do not have permission to assign asset custody."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    serial_number = request.data.get('serial_number')
    employee_code = request.data.get('employee_code')
    notes = request.data.get('notes', '')

    if not serial_number or not employee_code:
        return Response({"error": "Serial number and employee_code are required fields."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            asset = BaseAsset.objects.get(serial_number=serial_number)
            employee = Employee.objects.get(employee_code=employee_code)
            
            if asset.status != 'in_stock':
                return Response({"error": f"Asset with serial {serial_number} is already {asset.get_status_display()}"}, status=status.HTTP_400_BAD_REQUEST)

            ConsumerCustody.objects.create(
                asset=asset,
                employee=employee,
                action_type='issue',
                assignment_date=timezone.now().date(),
                assigned_by=request.user if request.user.is_authenticated else None,
                notes=notes
            )

            asset.status = 'assigned'
            asset.save()

            # Safely fetch branch/sector/department via employee.branch_structure
            bs = employee.branch_structure
            branch_name = getattr(bs.branch, 'name_en', getattr(bs.branch, 'name', None)) if bs and bs.branch else None
            sector_name = getattr(bs.sector, 'sector_name', getattr(bs.sector, 'name', None)) if bs and bs.sector else None
            dept_name = getattr(bs.department, 'name', None) if bs and bs.department else None

            # Create Inventory Transaction Log
            InventoryTransactionLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action_type='Decreased',
                item_type='asset',
                hardware_asset=asset,
                inventory_item=None,
                quantity_changed=-1,
                new_total_quantity=0,
                notes=notes or f"Asset {serial_number} issued to employee {employee.name_en or employee.name_ar or employee_code}",
                consumer=employee.name_en or employee.name_ar or str(employee_code),
                branch=str(branch_name) if branch_name else None,
                sector=str(sector_name) if sector_name else None,
                department=str(dept_name) if dept_name else None
            )

        return Response({"message": f"Asset {serial_number} successfully assigned to employee {employee_code}."}, status=status.HTTP_201_CREATED)

    except BaseAsset.DoesNotExist:
        return Response({"error": f"Asset with serial {serial_number} not found."}, status=status.HTTP_404_NOT_FOUND)
    except Employee.DoesNotExist:
        return Response({"error": f"Employee with code {employee_code} not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_asset_to_structure(request):
    """
    API view to issue an in-stock asset DIRECTLY to a Branch, Sector, or Department layout.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.add_consumercustody'):
        return Response(
            {"error": "You do not have permission to assign asset structure custody."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    serial_number = request.data.get('serial_number')
    structure_id = request.data.get('structure_id')
    notes = request.data.get('notes', '')

    if not serial_number or not structure_id:
        return Response(
            {"error": "Both 'serial_number' and 'structure_id' are required fields."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            asset = BaseAsset.objects.get(serial_number=serial_number)
            
            if asset.status != 'in_stock':
                return Response(
                    {"error": f"Asset {serial_number} cannot be assigned. Current status is: {asset.get_status_display() or asset.status}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                branch_structure = BranchStructure.objects.get(pk=structure_id)
            except BranchStructure.DoesNotExist:
                return Response(
                    {"error": f"Organizational Structure with ID {structure_id} does not exist."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            ConsumerCustody.objects.create(
                asset=asset,
                employee=None,
                branch_structure=branch_structure,
                action_type='issue',
                assignment_date=timezone.now().date(),
                assigned_by=request.user if request.user.is_authenticated else None,
                notes=notes
            )

            asset.status = 'assigned'
            asset.save()

            # Extract location details from the branch_structure relations
            branch_name = getattr(branch_structure.branch, 'name_en', getattr(branch_structure.branch, 'name', None)) if branch_structure.branch else None
            sector_name = getattr(branch_structure.sector, 'sector_name', getattr(branch_structure.sector, 'name', None)) if branch_structure.sector else None
            dept_name = getattr(branch_structure.department, 'name', None) if branch_structure.department else None

            # Create Inventory Transaction Log
            InventoryTransactionLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action_type='Deacreased',
                item_type='asset',
                hardware_asset=asset,
                inventory_item=None,
                quantity_changed=-1,
                new_total_quantity=0,
                notes=notes or f"Asset {serial_number} assigned to structure layout {structure_id}",
                consumer=None,
                branch=str(branch_name) if branch_name else None,
                sector=str(sector_name) if sector_name else None,
                department=str(dept_name) if dept_name else None
            )

        return Response(
            {"message": f"Asset {serial_number} has been successfully assigned to structure layout ID {structure_id}."}, 
            status=status.HTTP_201_CREATED
        )

    except BaseAsset.DoesNotExist:
        return Response({"error": f"Asset with serial {serial_number} not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def replace_consumer_asset(request):
    """
    API view to process hardware asset movements.
    - If action_type is 'issue' or 'upgrade': Requires a new serial to perform an immediate hardware swap.
    - If action_type is 'layoff' or 'retired': Does NOT require a new serial, accepts asset return, 
      and sets the old asset status directly to 'in_stock'.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.change_consumercustody'):
        return Response(
            {"error": "You do not have permission to replace or swap custody assets."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    old_serial = request.data.get('old_serial_number')
    new_serial = request.data.get('new_serial_number')
    requested_action = request.data.get('action_type', 'issue') 
    
    notes = request.data.get('notes', '')
    reason_input = request.data.get('reason', 'Hardware replacement / Swap')
    it_technician = request.user if request.user.is_authenticated else None

    # 1. Validation Safeguards
    if not old_serial:
        return Response({"error": "The old_serial_number is mandatory."}, status=status.HTTP_400_BAD_REQUEST)

    # Determine if this is an offboarding action (layoff or retired)
    is_offboarding = requested_action in ['layoff', 'retired']
    
    # If it is NOT an offboarding action, a new replacement asset is mandatory
    if not new_serial and not is_offboarding:
        return Response(
            {"error": f"A new_serial_number is required for '{requested_action}' transactions."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # Fetch the old asset
            old_asset = BaseAsset.objects.get(serial_number=old_serial)
            
            # Fetch the new replacement asset ONLY if it is passed in the payload
            new_asset = None
            if new_serial:
                new_asset = BaseAsset.objects.get(serial_number=new_serial)
                if new_asset.status != 'in_stock':
                    return Response({"error": f"Target replacement asset {new_serial} is not in stock"}, status=status.HTTP_400_BAD_REQUEST)

            # Search for the open historical trace (either 'issue' or 'upgrade')
            active_custody = old_asset.custody_history.filter(
                action_type__in=['issue', 'upgrade'], 
                return_date__isnull=True
            ).first()
            
            if not active_custody:
                return Response({"error": f"No active custody trace available for asset {old_serial}"}, status=status.HTTP_400_BAD_REQUEST)

            current_date = timezone.now().date()

            # 2. Close out the existing historical custody log
            active_custody.return_date = current_date
            swap_msg = f"Swapped with asset S/N: {new_serial}." if new_serial else "Asset collected back completely due to consumer status change."
            active_custody.notes = f"Closed: {swap_msg} Details: {notes or 'No extra notes provided.'}"
            active_custody.save()

            # 3. Dynamically build clean system audit notes for the 'return' log
            if requested_action == 'retired':
                system_notes = "Returned automatically because employee retired."
            elif requested_action == 'layoff':
                system_notes = "Returned automatically because employee was laid off."
            elif requested_action == 'upgrade':
                system_notes = f"Returned automatically because upgrade to asset S/N: {new_serial}."
            else:
                system_notes = f"Returned automatically due to replacement with asset S/N: {new_serial}."

            if notes:
                system_notes += f" User Notes: {notes}"

            # Create the 'return' movement entry in the tracking history
            ConsumerCustody.objects.create(
                asset=old_asset,
                employee=active_custody.employee,
                branch_structure=active_custody.branch_structure,
                action_type='return',
                assignment_date=current_date,
                assigned_by=it_technician,
                reason=reason_input,
                notes=system_notes
            )
            
            # 4. Update the Old Asset Status in base_asset (hardware_assets) table
            if is_offboarding or requested_action == 'upgrade':
                old_asset.status = 'in_stock'       # Sends directly back to inventory
            else:
                old_asset.status = 'maintenance'    # Standard issued replacements go to maintenance checkups
                
            old_asset.save()

            # 5. Handle issuing the NEW asset ONLY if it was provided in the Postman payload
            if new_asset:
                ConsumerCustody.objects.create(
                    asset=new_asset,
                    employee=active_custody.employee,
                    branch_structure=active_custody.branch_structure,
                    action_type='issue',
                    assignment_date=current_date,
                    assigned_by=it_technician,
                    reason=reason_input,
                    notes=f"Issued automatically to replace asset S/N: {old_serial}"
                )

                # Set new asset status to assigned
                new_asset.status = 'assigned'
                new_asset.save()

        # Dynamic return message structure
        msg = "Asset successfully returned and logged to inventory." if not new_serial else "Hardware replacement log committed successfully."
        return Response({"message": msg}, status=status.HTTP_200_OK)

    except BaseAsset.DoesNotExist:
        return Response({"error": "Failed to map requested serial numbers to existing objects."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def replace_structure_asset(request):
    """
    API view to process immediate hardware swap transactions safely for structural layout custody (Branch/Sector/Department).
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.change_consumercustody'):
        return Response(
            {"error": "You do not have permission to replace structural layout assets."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    old_serial = request.data.get('old_serial_number')
    new_serial = request.data.get('new_serial_number')
    notes = request.data.get('notes', 'Swapped via structural hardware replacement desk.')
    it_technician = request.user if request.user.is_authenticated else None

    if not old_serial or not new_serial:
        return Response({"error": "Both old and new serial numbers are mandatory."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            old_asset = BaseAsset.objects.get(serial_number=old_serial)
            new_asset = BaseAsset.objects.get(serial_number=new_serial)

            # 1️⃣ التحقق من أن الجهاز الجديد متاح بالمخزن
            if new_asset.status != 'in_stock':
                return Response({"error": f"Target replacement asset {new_serial} is not in stock"}, status=status.HTTP_400_BAD_REQUEST)

            # 2️⃣ جلب العهدة النشطة الخاصة بالمقر (باستخدام الحقل العكسي المتاح لديك للأصل)
            active_custody = old_asset.custody_history.filter(action_type='issue', return_date__isnull=True).first()
            if not active_custody:
                return Response({"error": f"No active custody trace available for asset {old_serial}"}, status=status.HTTP_400_BAD_REQUEST)

            # تفتيش أمني: للتأكد من أن هذه عهدة مكانية تابعة لهيكل وليست عهدة شخصية لموظف
            if not active_custody.branch_structure:
                return Response({"error": f"Asset {old_serial} is assigned to an employee. Please use the employee replacement endpoint instead."}, status=status.HTTP_400_BAD_REQUEST)

            current_date = timezone.now().date()

            # 3️⃣ إغلاق العهدة القديمة
            active_custody.return_date = current_date
            active_custody.notes = f"Closed: Swapped with asset S/N: {new_serial}. Details: {notes}"
            active_custody.save()

            # 4️⃣ تسجيل حركة إرجاع (return) للجهاز القديم بدون موظف (مع ربط الهيكل)
            ConsumerCustody.objects.create(
                asset=old_asset,
                employee=None,
                branch_structure=active_custody.branch_structure,
                action_type='return',
                assignment_date=current_date,
                assigned_by=it_technician,
                notes=f"Returned automatically due to replacement with asset S/N: {new_serial}"
            )
            
            # تحويل حظر الجهاز القديم للصيانة
            old_asset.status = 'maintenance'
            old_asset.save()

            # 5️⃣ تسجيل حركة صرف (issue) جديدة للجهاز البديل ونقل الـ branch_structure إليه تلقائياً
            ConsumerCustody.objects.create(
                asset=new_asset,
                employee=None,
                branch_structure=active_custody.branch_structure,  # 🌟 توريث المقر تلقائياً هنا
                action_type='issue',
                assignment_date=current_date,
                assigned_by=it_technician,
                notes=f"Issued automatically to replace asset S/N: {old_serial}"
            )

            # تحويل حالة الجهاز البديل إلى مصروف
            new_asset.status = 'assigned'
            new_asset.save()

        return Response({"message": "Structural hardware replacement log committed successfully."}, status=status.HTTP_200_OK)

    except BaseAsset.DoesNotExist:
        return Response({"error": "Failed to map requested serial numbers to existing objects."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_asset_history(request, serial_number):
    """
    API view to fetch the tracking log history for a SPECIFIC asset by its serial number.
    Supports both employee personal custody and structural layout assignment seamlessly.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view asset history logs."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Include direct 'branch_structure' relation alongside employee structure relations
        history = ConsumerCustody.objects.select_related(
            'asset', 
            'asset__category', 
            'asset__computerasset', 
            'employee',
            'employee__branch_structure',
            'branch_structure',
            'branch_structure__branch',
            'branch_structure__sector',
            'branch_structure__department',
            'assigned_by'
        ).filter(asset__serial_number=serial_number).order_by('-created_at')

        report = []
        for log in history:
            emp = log.employee
            asset = log.asset
            cat = asset.category if asset else None
            
            # 💡 Fallback to direct log.branch_structure if log.employee is None
            struct = log.branch_structure or (emp.branch_structure if emp else None)
            
            # 🛡️ Safe extraction for location details
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                branch_name = getattr(struct.branch, 'name_en', None) or getattr(struct.branch, 'branch_name', None) or str(struct.branch)
                
            sector_name = None
            if struct and getattr(struct, 'sector', None):
                sector_name = getattr(struct.sector, 'sector_name', None) or getattr(struct.sector, 'name', None) or str(struct.sector)
                
            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = getattr(struct.department, 'name', None) or str(struct.department)

            # 📦 Base asset metadata
            asset_data = {
                "asset_code": getattr(asset, 'asset_code', None) if asset else None,
                "category_name_en": cat.name_en if cat else None,
                "category_name_ar": cat.name_ar if cat else None,
                "brand": asset.brand if asset else None,
                "model_or_pn": asset.model_or_pn if asset else None,
                "serial_number": asset.serial_number if asset else None,
            }

            # 💻 Attach specs if category is computer/laptop
            if cat and cat.name_en.lower() in ['computer', 'pc', 'laptop']:
                comp_specs = getattr(asset, 'computerasset', None)
                if comp_specs:
                    asset_data["specs"] = {
                        "processor": getattr(comp_specs, 'processor', None),
                        "ram": getattr(comp_specs, 'ram', None),
                        "storage": getattr(comp_specs, 'storage', None),
                        "os": getattr(comp_specs, 'os', None),
                    }

            # Assemble log entry
            report.append({
                "custody_id": log.id,
                "action_type": log.action_type,
                "action_display": log.get_action_type_display() if hasattr(log, 'get_action_type_display') else log.action_type,
                "action_date": log.assignment_date,
                "return_date": log.return_date,
                
                "assignment_target": {
                    "type": "employee" if emp else "structure",
                    "structure_id": struct.id if struct else None,
                    "branch_name": branch_name,
                    "sector_name": sector_name,
                    "department_name": department_name,
                    "employee_details": {
                        "employee_code": emp.employee_code,
                        "name_ar": emp.name_ar,
                        "name_en": emp.name_en,
                    } if emp else None
                },
                
                "asset": asset_data,
                "notes": log.notes,
                "operator": log.assigned_by.username if log.assigned_by else "System"
            })

        return Response(report, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_global_custody_history(request):
    """
    API view to fetch the complete tracking log history for ALL assets and consumers.
    Optimized performance to handle both employee personal custody and direct structural layouts,
    explicitly including tracking duration timelines.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view global custody history."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Optimizing with select_related for structural layouts and employees
        global_history = ConsumerCustody.objects.select_related(
            'asset', 
            'asset__category', 
            'employee__branch_structure', 
            'branch_structure',  
            'assigned_by'
        ).all().order_by('-created_at')

        report = []
        for log in global_history:
            emp = log.employee
            asset = log.asset
            cat = asset.category if asset else None
            
            # Resolve the active operational structural tier
            struct = log.branch_structure if log.branch_structure else (emp.branch_structure if emp else None)
            
            # Safe extraction for Branch Name
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                branch_name = (
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )
            sector_name = None
            if struct and getattr(struct, 'sector', None):
                sector_name = (
                    getattr(struct.sector, 'name', None) or 
                    getattr(struct.sector, 'sector_name', None) or 
                    getattr(struct.sector, 'name', None) or 
                    str(struct.sector)
                )
            # Safe extraction for Department Name
            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = (
                    getattr(struct.department, 'name', None) or 
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            # Determine the dynamic display string and type details
            if emp:
                assigned_to_display = getattr(emp, 'name_en', None) or getattr(emp, 'name_ar', None) or f"Emp Code: {emp.employee_code}"
                assignment_type = "employee"
            else:
                assigned_to_display = branch_name or "Unknown Location"
                assignment_type = "structure"

            # Building the flat/clean payload for the frontend table
            report.append({
                "custody_id": log.id,
                "action_type": log.action_type,
                "action_display": log.get_action_type_display() if hasattr(log, 'get_action_type_display') else log.action_type,
                
                # 🌟 Core Timeline Dates from custody_consumercustody
                "assignment_date": log.assignment_date,  # When the assignment started
                "return_date": log.return_date,          # When the asset was returned (null if active)
                "created_at": log.created_at,            # System timestamp
                "updated_at": log.updated_at,            # Last update timestamp
                
                # Core Asset Details
                "brand": asset.brand if asset else None,
                "model_or_pn": asset.model_or_pn if asset else None,
                "serial_number": asset.serial_number if asset else None,
                
                # Assignment Mapping Details
                "assignment_type": assignment_type,
                "assigned_to": assigned_to_display, 
                "employee_name_en": emp.name_en if emp else None,
                "employee_name_ar": emp.name_ar if emp else None,
                "employee_code": emp.employee_code if emp else None,
                
                # Comprehensive target metadata structure 
                "assignment_target": {
                    "type": assignment_type,
                    "structure_id": struct.id if struct else None,
                    "branch_name": branch_name,
                    "sector_name": sector_name,
                    "department_name": department_name,
                    "employee_details": {
                        "employee_code": emp.employee_code,
                        "name_ar": emp.name_ar,
                        "name_en": emp.name_en,
                    } if emp else None
                },
                
                "asset_details": {
                    "id": asset.asset_code if asset else None,
                    "asset_code": asset.asset_code if asset else None,
                    "category_name_en": cat.name_en if cat else None,
                    "category_name_ar": cat.name_ar if cat else None,
                },
                
                "notes": log.notes,
                "operator": log.assigned_by.username if log.assigned_by else "System"
            })

        return Response(report, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_active_assignments(request):
    """
    API view to get all currently assigned hardware assets and the entities holding them.
    Filters out returned assets (return_date IS NULL) and supports both employee and direct structural custody.
    Explicitly joins with ComputerAsset from the hw_spec app to return asset specs.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view active assignments."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # 🌟 Cleaned select_related (removed non-existent 'branch_structure')
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset',
            'employee__branch_structure',
            'assigned_by'
        ).order_by('-assignment_date')

        data = []
        for custody in active_assignments:
            emp = custody.employee
            asset = custody.asset
            
            # 💡 Derive branch structure safely via employee
            struct = getattr(emp, 'branch_structure', None) if emp else None
            
            # 🛡️ Safe extraction for location details
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                branch_name = (
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )
            
            sector_name = None
            if struct and getattr(struct, 'sector', None):
                sector_name = (
                    getattr(struct.sector, 'sector_name', None) or 
                    getattr(struct.sector, 'name', None) or 
                    getattr(struct.sector, 'sec_name', None) or 
                    str(struct.sector)
                )    
            
            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = (
                    getattr(struct.department, 'name_en', None) or 
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            # 🛠️ Multi-Table Inheritance: Extract specialized specifications from ComputerAsset
            asset_specs = {}
            if asset:
                comp_subclass = None
                
                # 1. Standard Django reverse lookup matching lowercased class name
                if hasattr(asset, 'computerasset'):
                    try:
                        comp_subclass = asset.computerasset
                    except Exception:
                        pass
                
                # 2. Fallback direct DB lookup using primary key link (asset_code)
                if not comp_subclass:
                    try:
                        from apps.hardware_specs.models import ComputerAsset
                        comp_subclass = ComputerAsset.objects.filter(
                            baseasset_ptr_id=asset.asset_code
                        ).first()
                    except Exception:
                        pass

                # Populate data fields
                if comp_subclass:
                    asset_specs = {
                        "pc_type": getattr(comp_subclass, 'pc_type', None),
                        "processor": getattr(comp_subclass, 'processor', None),
                        "memory_ram": getattr(comp_subclass, 'memory_ram', None),
                        "hard_disk": getattr(comp_subclass, 'hard_disk', None),
                        "bag_brand": getattr(comp_subclass, 'bag_brand', None),
                        "bag_model_or_description": (
                            getattr(comp_subclass, 'bag_model_or_description', None) or 
                            getattr(comp_subclass, 'bag_model_or_descrp', None)
                        ),
                    }

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                
                "employee": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "branch": branch_name,
                    "sector": sector_name,
                    "department": department_name,
                    "assignment_type": "employee" if emp else "structure"
                },
                
                "asset": {
                    "id": asset.asset_code if asset else None,  # Updated to asset_code
                    "asset_code": asset.asset_code if asset else None,
                    "serial_number": asset.serial_number if asset else None,
                    "brand": asset.brand if asset else None,
                    "model_or_pn": asset.model_or_pn if asset else None,
                    "status": asset.status if asset else None,
                    "specs": asset_specs
                }
            })

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assigned_assets_count(request):
    """
    API view to return the total number of currently assigned hardware assets.
    Matches the business logic of active assignments (issued and not yet returned).
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view assignment stats."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # 🚀 Extremely fast because it executes a single SELECT COUNT(*) query
        assigned_count = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).count()

        return Response(
            {
                "status": "success",
                "assigned_assets_count": assigned_count
            }, 
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

from .models import ConsumerCustody

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_filtered_and_searched_assets_in_custody(request):
    """
    Function-based API view supporting global free-text search, multi-field dropdown 
    filtering, category-specific spec resolution (Computer, Monitor, Printer, Tablet), 
    and optional unpaginated exports via `?all=true`.
    """
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view assignments."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # 1. Query Parameters Extraction
    category_name = request.query_params.get('name', None)
    search_query = request.query_params.get('search', None)
    export_all = request.query_params.get('all', 'false').lower() == 'true'

    # Filter params for dropdowns (support string names & numeric IDs)
    filter_brand = request.query_params.get('brand', None)
    filter_pc_type = request.query_params.get('pc_type', None)
    
    filter_branch = request.query_params.get('branch', None)
    filter_branch_id = request.query_params.get('branch_id', None)
    
    filter_sector = request.query_params.get('sector', None)
    filter_sector_id = request.query_params.get('sector_id', None)
    
    filter_department = request.query_params.get('department', None)
    filter_dept_id = request.query_params.get('department_id', None)

    try:
        # Base Queryset targeting active custody assignments
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset__category', 
            'asset__computerasset',
            'asset__monitorasset',
            'asset__printerasset',
            'asset__tabletasset',
            'employee__branch_structure',
            'branch_structure',
            'branch_structure__branch',
            'branch_structure__sector',
            'branch_structure__department',
            'employee__branch_structure__branch',
            'employee__branch_structure__sector',
            'employee__branch_structure__department'
        )

        # 2. Category Filter
        if category_name and category_name.strip():
            cat_val = category_name.strip()
            active_assignments = active_assignments.filter(
                Q(asset__category__name_en__icontains=cat_val) | 
                Q(asset__category__name_ar__icontains=cat_val)
            )

        # 3. Structured Dropdown Filters
        if filter_brand and filter_brand.strip():
            active_assignments = active_assignments.filter(asset__brand__iexact=filter_brand.strip())

        if filter_pc_type and filter_pc_type.strip():
            active_assignments = active_assignments.filter(asset__computerasset__pc_type__iexact=filter_pc_type.strip())

        # Branch Filtering
        if filter_branch_id and str(filter_branch_id).isdigit():
            b_id = int(filter_branch_id)
            active_assignments = active_assignments.filter(
                Q(branch_structure__branch_id=b_id) |
                Q(employee__branch_structure__branch_id=b_id)
            )
        elif filter_branch and filter_branch.strip():
            b_val = filter_branch.strip()
            if b_val.isdigit():
                active_assignments = active_assignments.filter(
                    Q(branch_structure__branch_id=int(b_val)) |
                    Q(employee__branch_structure__branch_id=int(b_val))
                )
            else:
                active_assignments = active_assignments.filter(
                    Q(branch_structure__branch__name_en__icontains=b_val) |
                    Q(branch_structure__branch__name_ar__icontains=b_val) |
                    Q(employee__branch_structure__branch__name_en__icontains=b_val) |
                    Q(employee__branch_structure__branch__name_ar__icontains=b_val)
                )

        # Sector Filtering
        if filter_sector_id and str(filter_sector_id).isdigit():
            s_id = int(filter_sector_id)
            active_assignments = active_assignments.filter(
                Q(branch_structure__sector_id=s_id) |
                Q(employee__branch_structure__sector_id=s_id)
            )
        elif filter_sector and filter_sector.strip():
            s_val = filter_sector.strip()
            if s_val.isdigit():
                active_assignments = active_assignments.filter(
                    Q(branch_structure__sector_id=int(s_val)) |
                    Q(employee__branch_structure__sector_id=int(s_val))
                )
            else:
                active_assignments = active_assignments.filter(
                    Q(branch_structure__sector__sector_name__icontains=s_val) |
                    Q(branch_structure__sector__name_en__icontains=s_val) |
                    Q(employee__branch_structure__sector__sector_name__icontains=s_val) |
                    Q(employee__branch_structure__sector__name_en__icontains=s_val)
                )

        # Department Filtering
        if filter_dept_id and str(filter_dept_id).isdigit():
            d_id = int(filter_dept_id)
            active_assignments = active_assignments.filter(
                Q(branch_structure__department_id=d_id) |
                Q(employee__branch_structure__department_id=d_id)
            )
        elif filter_department and filter_department.strip():
            d_val = filter_department.strip()
            if d_val.isdigit():
                active_assignments = active_assignments.filter(
                    Q(branch_structure__department_id=int(d_val)) |
                    Q(employee__branch_structure__department_id=int(d_val))
                )
            else:
                active_assignments = active_assignments.filter(
                    Q(branch_structure__department__name__icontains=d_val) |
                    Q(branch_structure__department__name_en__icontains=d_val) |
                    Q(employee__branch_structure__department__name__icontains=d_val) |
                    Q(employee__branch_structure__department__name_en__icontains=d_val)
                )

        # 4. Global Search Filter (Updated to use asset_code instead of id)
        if search_query and search_query.strip():
            term = search_query.strip()
            
            search_conditions = Q(
                Q(asset__serial_number__icontains=term) |
                Q(asset__brand__icontains=term) |
                Q(asset__model_or_pn__icontains=term) |
                Q(employee__employee_code__icontains=term) |
                Q(employee__name_en__icontains=term) |
                Q(employee__name_ar__icontains=term) |
                Q(branch_structure__branch__name_en__icontains=term) |
                Q(branch_structure__branch__name_ar__icontains=term) |
                Q(employee__branch_structure__branch__name_en__icontains=term) |
                Q(employee__branch_structure__branch__name_ar__icontains=term) |
                Q(asset__computerasset__processor__icontains=term) |
                Q(asset__computerasset__memory_ram__icontains=term) |
                Q(asset__computerasset__hard_disk__icontains=term) |
                Q(asset__computerasset__pc_type__icontains=term) |
                Q(asset__printerasset__ip_address_eth__icontains=term)
            )

            # Updated asset ID lookup to asset_code
            if term.isdigit():
                search_conditions |= Q(asset__asset_code=int(term))
            else:
                search_conditions |= Q(asset__asset_code__icontains=term)

            active_assignments = active_assignments.filter(search_conditions)

        active_assignments = active_assignments.distinct().order_by('-assignment_date')

        # 5. Pagination vs Unpaginated Resolution
        is_filtered = any([
            search_query, filter_brand, filter_pc_type, 
            filter_branch, filter_branch_id, 
            filter_sector, filter_sector_id, 
            filter_department, filter_dept_id
        ])

        if export_all or is_filtered:
            target_assignments = active_assignments
            page = None
            paginator = None
        else:
            paginator = PageNumberPagination()
            page = paginator.paginate_queryset(active_assignments, request)
            target_assignments = page if page is not None else active_assignments

        # 6. Data Construction and Specification Extraction
        data = []
        for custody in target_assignments:
            emp = custody.employee
            asset = custody.asset
            cat = asset.category if asset else None

            # Resolve Branch Structure
            struct = custody.branch_structure if custody.branch_structure else (emp.branch_structure if emp else None)

            # Structure Name Extraction
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                b = struct.branch
                branch_name = getattr(b, 'name_en', None) or getattr(b, 'branch_name', None) or getattr(b, 'name_ar', None)

            sector_name = None
            if struct and getattr(struct, 'sector', None):
                s = struct.sector
                sector_name = getattr(s, 'sector_name', None) or getattr(s, 'name_en', None) or getattr(s, 'name', None)

            department_name = None
            if struct and getattr(struct, 'department', None):
                d = struct.department
                department_name = getattr(d, 'name', None) or getattr(d, 'name_en', None) or getattr(d, 'department_name', None)

            # Specification Dictionary Population
            specs_dict = {}
            if asset:
                comp = getattr(asset, 'computerasset', None) or getattr(asset, 'computer', None)
                if comp:
                    specs_dict = {
                        "spec_type": "computer",
                        "pc_type": getattr(comp, 'pc_type', None),
                        "processor": getattr(comp, 'processor', None),
                        "ram": getattr(comp, 'memory_ram', None),
                        "hard_disk": getattr(comp, 'hard_disk', None),
                        "bag_brand": getattr(comp, 'bag_brand', None),
                        "bag_model_or_description": getattr(comp, 'bag_model_or_description', None),
                        "keyboard_brand": getattr(comp, 'keyboard_brand', None),
                        "keyboard_model": getattr(comp, 'keyboard_model', None),
                        "keyboard_serial": getattr(comp, 'keyboard_serial', None),
                        "monitor_brand": getattr(comp, 'monitor_brand', None),
                        "monitor_inches": getattr(comp, 'monitor_inches', None),
                        "monitor_model": getattr(comp, 'monitor_model', None),
                        "monitor_serial": getattr(comp, 'monitor_serial', None),
                        "mouse_brand": getattr(comp, 'mouse_brand', None),
                        "mouse_model": getattr(comp, 'mouse_model', None),
                        "mouse_serial": getattr(comp, 'mouse_serial', None),
                    }
                elif getattr(asset, 'monitorasset', None) or getattr(asset, 'monitor', None):
                    mon = getattr(asset, 'monitorasset', None) or getattr(asset, 'monitor', None)
                    specs_dict = {
                        "spec_type": "monitor",
                        "inches": getattr(mon, 'inches', None),
                        "is_meeting_room_tv": getattr(mon, 'is_meeting_room_tv', None),
                        "is_curved": getattr(mon, 'is_curved', None),
                        "color": getattr(mon, 'color', None),
                        "location_details": getattr(mon, 'location_details', None),
                        "part_number": getattr(mon, 'part_number', None),
                    }
                elif getattr(asset, 'printerasset', None) or getattr(asset, 'printer', None):
                    ptr = getattr(asset, 'printerasset', None) or getattr(asset, 'printer', None)
                    specs_dict = {
                        "spec_type": "printer",
                        "printer_type": getattr(ptr, 'printer_type', None),
                        "connection_type": getattr(ptr, 'connection_type', None),
                        "active_connection": getattr(ptr, 'active_connection', None),
                        "cartridge_color": getattr(ptr, 'cartridge_color', None),
                        "cartridge_number": getattr(ptr, 'cartridge_number', None),
                        "ink_details": getattr(ptr, 'ink_details', None),
                        "ip_address_eth": getattr(ptr, 'ip_address_eth', None),
                        "mac_address_eth": getattr(ptr, 'mac_address_eth', None),
                        "mac_address_wifi": getattr(ptr, 'mac_address_wifi', None),
                        "multifunctions": getattr(ptr, 'multifunctions', None),
                        "printer_color": getattr(ptr, 'printer_color', None),
                        "technology": getattr(ptr, 'technology', None),
                    }
                elif getattr(asset, 'tabletasset', None) or getattr(asset, 'tablet', None):
                    tab = getattr(asset, 'tabletasset', None) or getattr(asset, 'tablet', None)
                    specs_dict = {
                        "spec_type": "tablet",
                        "device_item_type": getattr(tab, 'device_item_type', None),
                        "storage_ram": getattr(tab, 'storage_ram', None),
                        "screen_color_specs": getattr(tab, 'screen_color_specs', None),
                    }

            # Updated asset dictionary to return asset_code
            asset_data = {
                "id": asset.asset_code if asset else None,
                "asset_code": asset.asset_code if asset else None,
                "serial_number": asset.serial_number if asset else None,
                "brand": asset.brand if asset else None,
                "model_or_pn": asset.model_or_pn if asset else None,
                "status": getattr(asset, 'status', None) if asset else None,
                "category": {
                    "id": cat.id if cat else None,
                    "name_en": getattr(cat, 'name_en', None) if cat else None,
                    "name_ar": getattr(cat, 'name_ar', None) if cat else None,
                },
                "specs": specs_dict
            }

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                "asset_id": asset.asset_code if asset else None,
                "employee": {
                    "employee_code": getattr(emp, 'employee_code', None) if emp else None,
                    "name_en": getattr(emp, 'name_en', None) if emp else None,
                    "name_ar": getattr(emp, 'name_ar', None) if emp else None,
                    "structure_id": struct.id if struct else None,
                    "assignment_type": "employee" if emp else "structure",
                    "branch_name": branch_name,
                    "sector_name": sector_name,
                    "department_name": department_name
                },
                "asset": asset_data
            })

        if page is not None and not export_all:
            return paginator.get_paginated_response(data)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )     

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

# Ensure ConsumerCustody is imported from your custody models
# from .models import ConsumerCustody

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assigned_assets_by_category(request):
    """
    Function-based API view supporting standard pagination as well as 
    unpaginated export downloads via `?all=true`. Returns Category-specific specs.
    Handles asset status mapping and safely checks model string representations.
    """
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view assignments by category."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    category_name = request.query_params.get('name', None)
    export_all = request.query_params.get('all', 'false').lower() == 'true'

    if not category_name:
        return Response(
            {"error": "Please provide a 'name' parameter (e.g., ?name=Computer)"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset__category', 
            'asset__computerasset',
            'asset__monitorasset',
            'asset__printerasset',
            'asset__tabletasset',
            'employee__branch_structure',
            'branch_structure',
            'branch_structure__branch',
            'branch_structure__sector',
            'branch_structure__department',
            'employee__branch_structure__branch',
            'employee__branch_structure__sector',
            'employee__branch_structure__department'
        ).filter(
            Q(asset__category__name_en__icontains=category_name) | 
            Q(asset__category__name_ar__icontains=category_name)
        ).order_by('-assignment_date')

        # Handle unpaginated vs paginated dataset resolution
        if export_all:
            target_assignments = active_assignments
            page = None
        else:
            paginator = PageNumberPagination()
            page = paginator.paginate_queryset(active_assignments, request)
            target_assignments = page if page is not None else active_assignments

        data = []
        for custody in target_assignments:
            emp = custody.employee
            asset = custody.asset
            cat = asset.category if asset else None

            # Resolve structure (either from explicit custody assignment or employee structure)
            struct = custody.branch_structure if custody.branch_structure else (emp.branch_structure if emp else None)

            # 1. Branch Name Mapping
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                b = struct.branch
                branch_name = getattr(b, 'name_en', None) or getattr(b, 'branch_name', None) or getattr(b, 'name_ar', None)

            # 2. Sector Name Mapping
            sector_name = None
            if struct and getattr(struct, 'sector', None):
                s = struct.sector
                sector_name = getattr(s, 'sector_name', None) or getattr(s, 'name_en', None) or getattr(s, 'name', None)

            # 3. Department Name Mapping
            department_name = None
            if struct and getattr(struct, 'department', None):
                d = struct.department
                department_name = getattr(d, 'name', None) or getattr(d, 'name_en', None) or getattr(d, 'department_name', None)

            # Category-Specific Specs Extraction
            specs_dict = {}
            if asset:
                # Computers / Laptops / PCs
                comp = getattr(asset, 'computerasset', None) or getattr(asset, 'computer', None)
                if comp:
                    specs_dict = {
                        "spec_type": "computer",
                        "pc_type": getattr(comp, 'pc_type', None),
                        "processor": getattr(comp, 'processor', None),
                        "ram": getattr(comp, 'memory_ram', None),
                        "hard_disk": getattr(comp, 'hard_disk', None),
                        "bag_brand": getattr(comp, 'bag_brand', None),
                        "bag_model_or_description": getattr(comp, 'bag_model_or_description', None),
                        "keyboard_brand": getattr(comp, 'keyboard_brand', None),
                        "keyboard_model": getattr(comp, 'keyboard_model', None),
                        "keyboard_serial": getattr(comp, 'keyboard_serial', None),
                        "monitor_brand": getattr(comp, 'monitor_brand', None),
                        "monitor_inches": getattr(comp, 'monitor_inches', None),
                        "monitor_model": getattr(comp, 'monitor_model', None),
                        "monitor_serial": getattr(comp, 'monitor_serial', None),
                        "mouse_brand": getattr(comp, 'mouse_brand', None),
                        "mouse_model": getattr(comp, 'mouse_model', None),
                        "mouse_serial": getattr(comp, 'mouse_serial', None),
                    }
                # Monitors
                elif getattr(asset, 'monitorasset', None) or getattr(asset, 'monitor', None):
                    mon = getattr(asset, 'monitorasset', None) or getattr(asset, 'monitor', None)
                    specs_dict = {
                        "spec_type": "monitor",
                        "inches": getattr(mon, 'inches', None),
                        "is_meeting_room_tv": getattr(mon, 'is_meeting_room_tv', None),
                        "is_curved": getattr(mon, 'is_curved', None),
                        "color": getattr(mon, 'color', None),
                        "location_details": getattr(mon, 'location_details', None),
                        "part_number": getattr(mon, 'part_number', None),
                    }
                # Printers
                elif getattr(asset, 'printerasset', None) or getattr(asset, 'printer', None):
                    ptr = getattr(asset, 'printerasset', None) or getattr(asset, 'printer', None)
                    specs_dict = {
                        "spec_type": "printer",
                        "printer_type": getattr(ptr, 'printer_type', None),
                        "connection_type": getattr(ptr, 'connection_type', None),
                        "active_connection": getattr(ptr, 'active_connection', None),
                        "cartridge_color": getattr(ptr, 'cartridge_color', None),
                        "cartridge_number": getattr(ptr, 'cartridge_number', None),
                        "ink_details": getattr(ptr, 'ink_details', None),
                        "ip_address_eth": getattr(ptr, 'ip_address_eth', None),
                        "mac_address_eth": getattr(ptr, 'mac_address_eth', None),
                        "mac_address_wifi": getattr(ptr, 'mac_address_wifi', None),
                        "multifunctions": getattr(ptr, 'multifunctions', None),
                        "printer_color": getattr(ptr, 'printer_color', None),
                        "technology": getattr(ptr, 'technology', None),
                    }
                # Tablets
                elif getattr(asset, 'tabletasset', None) or getattr(asset, 'tablet', None):
                    tab = getattr(asset, 'tabletasset', None) or getattr(asset, 'tablet', None)
                    specs_dict = {
                        "spec_type": "tablet",
                        "device_item_type": getattr(tab, 'device_item_type', None),
                        "storage_ram": getattr(tab, 'storage_ram', None),
                        "screen_color_specs": getattr(tab, 'screen_color_specs', None),
                    }

            asset_data = {
                "id": asset.id if asset else None,
                "serial_number": asset.serial_number if asset else None,
                "brand": asset.brand if asset else None,
                "model_or_pn": asset.model_or_pn if asset else None,
                "status": getattr(asset, 'status', None) if asset else None,
                "category": {
                    "id": cat.id if cat else None,
                    "name_en": getattr(cat, 'name_en', None) if cat else None,
                    "name_ar": getattr(cat, 'name_ar', None) if cat else None,
                },
                "specs": specs_dict
            }

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                "asset_id": asset.id if asset else None,
                "employee": {
                    "employee_code": getattr(emp, 'employee_code', None) if emp else None,
                    "name_en": getattr(emp, 'name_en', None) if emp else None,
                    "name_ar": getattr(emp, 'name_ar', None) if emp else None,
                    "structure_id": struct.id if struct else None,
                    "assignment_type": "employee" if emp else "structure",
                    "branch_name": branch_name,
                    "sector_name": sector_name,
                    "department_name": department_name
                },
                "asset": asset_data
            })

        if page is not None and not export_all:
            return paginator.get_paginated_response(data)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        
                
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_custody_by_serial(request, serial_number):
    """
    Looks up custody details using serial_number, asset_code, or primary key.
    Supports both live employee custody and structural branch assignments.
    """
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view custody entries."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # 1️⃣ Support lookup by serial_number OR asset_code OR Primary Key (pk)
    try:
        asset = BaseAsset.objects.select_related('category').get(
            Q(serial_number=serial_number) | 
            Q(asset_code=serial_number) | 
            Q(pk=serial_number if serial_number.isdigit() else None)
        )
    except BaseAsset.DoesNotExist:
        return Response(
            {"error": f"Device with identifier '{serial_number}' not found."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    # 2️⃣ Fetch active custody safely without invalid select_related fields
    active_custody = ConsumerCustody.objects.select_related(
        'employee',
        'asset'
    ).filter(
        asset=asset,
        action_type='issue',
        return_date__isnull=True
    ).order_by('-created_at').first()

    device_details = {
        "asset_code": asset.asset_code,
        "serial_number": asset.serial_number,
        "brand": asset.brand,
        "model_or_pn": asset.model_or_pn,
        "status": asset.status,
        "category_name": asset.category.name_en if asset.category else None
    }

    # 3️⃣ Return early if asset is in stock
    if not active_custody or not active_custody.employee:
        return Response({
            "message": "Device exists and is currently available in stock.",
            "custody_status": "in_stock",
            "device_details": device_details
        }, status=status.HTTP_200_OK)

    # 4️⃣ Safely derive location metadata from employee
    emp = active_custody.employee
    struct = getattr(emp, 'branch_structure', None) or getattr(emp, 'branch', None)

    branch_name = None
    sector_name = None
    department_name = None

    if struct:
        branch_obj = getattr(struct, 'branch', struct)
        branch_name = getattr(branch_obj, 'name_en', None) or getattr(branch_obj, 'name', None) or str(branch_obj)

        sector_obj = getattr(struct, 'sector', None)
        if sector_obj:
            sector_name = getattr(sector_obj, 'sector_name', None) or getattr(sector_obj, 'name', None) or str(sector_obj)

        dept_obj = getattr(struct, 'department', None)
        if dept_obj:
            department_name = getattr(dept_obj, 'name', None) or str(dept_obj)

    # 5️⃣ Build output response
    return Response({
        "message": "Device is currently deployed.",
        "custody_status": "assigned",
        "assignment_details": {
            "custody_id": active_custody.id,
            "assignment_date": active_custody.assignment_date,
            "assignment_type": "employee",
            "notes": active_custody.notes,
            "location": {
                "structure_id": getattr(struct, 'id', None),
                "branch_name": branch_name,
                "sector_name": sector_name,
                "department_name": department_name,
            },
            "employee_details": {
                "employee_code": emp.employee_code,
                "name_en": emp.name_en,
                "name_ar": emp.name_ar,
            }
        },
        "device_details": device_details
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assigned_assets_by_category_all(request):
    """
    Function-based API view:
    - Supports global search (`search`) across assets, employees, specs, and structures.
    - Supports explicit dropdown filters via string names or numeric IDs (brand, pc_type, branch/branch_id, sector/sector_id, department/department_id).
    - Disables pagination if `search` or any dropdown filter is active.
    """
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view assignments by category."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    category_name = request.query_params.get('name', None)
    search_query = request.query_params.get('search', None)
    
    # Dropdown Filter Parameters
    filter_brand = request.query_params.get('brand', None)
    filter_pc_type = request.query_params.get('pc_type', None)
    
    # Support both String names & Numeric IDs
    filter_branch = request.query_params.get('branch', None)
    filter_branch_id = request.query_params.get('branch_id', None)
    
    filter_sector = request.query_params.get('sector', None)
    filter_sector_id = request.query_params.get('sector_id', None)
    
    filter_department = request.query_params.get('department', None)
    filter_dept_id = request.query_params.get('department_id', None)
    
    if not category_name:
        return Response(
            {"error": "Please provide a 'name' parameter (e.g., ?name=pc)"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset__category', 
            'asset__computerasset',  
            'employee__branch_structure',
            'branch_structure',
            'branch_structure__branch',
            'branch_structure__sector',
            'branch_structure__department',
            'employee__branch_structure__branch',
            'employee__branch_structure__sector',
            'employee__branch_structure__department'
        ).filter(
            Q(asset__category__name_en__icontains=category_name) | 
            Q(asset__category__name_ar__icontains=category_name)
        )

        # 🎯 1. Structured Dropdown Filters

        # Brand Filter
        if filter_brand and filter_brand.strip():
            active_assignments = active_assignments.filter(asset__brand__iexact=filter_brand.strip())

        # PC Type Filter
        if filter_pc_type and filter_pc_type.strip():
            active_assignments = active_assignments.filter(asset__computerasset__pc_type__iexact=filter_pc_type.strip())

        # Branch Filter (Handles IDs & String Names safely)
        if filter_branch_id and str(filter_branch_id).isdigit():
            b_id = int(filter_branch_id)
            active_assignments = active_assignments.filter(
                Q(branch_structure__branch_id=b_id) |
                Q(employee__branch_structure__branch_id=b_id)
            )
        elif filter_branch and filter_branch.strip():
            b_val = filter_branch.strip()
            if b_val.isdigit():
                active_assignments = active_assignments.filter(
                    Q(branch_structure__branch_id=int(b_val)) |
                    Q(employee__branch_structure__branch_id=int(b_val))
                )
            else:
                active_assignments = active_assignments.filter(
                    Q(branch_structure__branch__name_en__icontains=b_val) |
                    Q(branch_structure__branch__name_ar__icontains=b_val) |
                    Q(employee__branch_structure__branch__name_en__icontains=b_val) |
                    Q(employee__branch_structure__branch__name_ar__icontains=b_val)
                )

        # Sector Filter (Handles IDs & String Names safely)
        if filter_sector_id and str(filter_sector_id).isdigit():
            s_id = int(filter_sector_id)
            active_assignments = active_assignments.filter(
                Q(branch_structure__sector_id=s_id) |
                Q(employee__branch_structure__sector_id=s_id)
            )
        elif filter_sector and filter_sector.strip():
            s_val = filter_sector.strip()
            if s_val.isdigit():
                active_assignments = active_assignments.filter(
                    Q(branch_structure__sector_id=int(s_val)) |
                    Q(employee__branch_structure__sector_id=int(s_val))
                )
            else:
                active_assignments = active_assignments.filter(
                    Q(branch_structure__sector__name_en__icontains=s_val) |
                    Q(branch_structure__sector__name_ar__icontains=s_val) |
                    Q(employee__branch_structure__sector__name_en__icontains=s_val) |
                    Q(employee__branch_structure__sector__name_ar__icontains=s_val)
                )

        # Department Filter (Handles IDs & String Names safely)
        if filter_dept_id and str(filter_dept_id).isdigit():
            d_id = int(filter_dept_id)
            active_assignments = active_assignments.filter(
                Q(branch_structure__department_id=d_id) |
                Q(employee__branch_structure__department_id=d_id)
            )
        elif filter_department and filter_department.strip():
            d_val = filter_department.strip()
            if d_val.isdigit():
                active_assignments = active_assignments.filter(
                    Q(branch_structure__department_id=int(d_val)) |
                    Q(employee__branch_structure__department_id=int(d_val))
                )
            else:
                active_assignments = active_assignments.filter(
                    Q(branch_structure__department__name_en__icontains=d_val) |
                    Q(branch_structure__department__name_ar__icontains=d_val) |
                    Q(employee__branch_structure__department__name_en__icontains=d_val) |
                    Q(employee__branch_structure__department__name_ar__icontains=d_val)
                )

        # 🔍 2. Free-text Search Filter
        if search_query and search_query.strip():
            search_term = search_query.strip()
            active_assignments = active_assignments.filter(
                Q(asset__serial_number__icontains=search_term) |
                Q(asset__brand__icontains=search_term) |
                Q(asset__model_or_pn__icontains=search_term) |
                Q(employee__employee_code__icontains=search_term) |
                Q(employee__name_en__icontains=search_term) |
                Q(employee__name_ar__icontains=search_term) |
                Q(branch_structure__branch__name_en__icontains=search_term) |
                Q(branch_structure__branch__name_ar__icontains=search_term) |
                Q(employee__branch_structure__branch__name_en__icontains=search_term) |
                Q(employee__branch_structure__branch__name_ar__icontains=search_term) |
                Q(asset__computerasset__processor__icontains=search_term) |
                Q(asset__computerasset__memory_ram__icontains=search_term) |
                Q(asset__computerasset__hard_disk__icontains=search_term) |
                Q(asset__computerasset__pc_type__icontains=search_term)
            )

        active_assignments = active_assignments.distinct().order_by('-assignment_date')

        # 🌐 3. Pagination Logic (Only paginate if NO search and NO filters are active)
        is_filtered = any([
            search_query, 
            filter_brand, 
            filter_pc_type, 
            filter_branch,
            filter_branch_id,
            filter_sector,
            filter_sector_id,
            filter_department,
            filter_dept_id
        ])

        page = None
        paginator = None

        if not is_filtered:
            paginator = PageNumberPagination()
            page = paginator.paginate_queryset(active_assignments, request)

        target_assignments = page if page is not None else active_assignments

        # 📦 4. Response Data Serialization
        data = []
        for custody in target_assignments:
            emp = custody.employee
            asset = custody.asset
            cat = asset.category if asset else None
            
            struct = custody.branch_structure if custody.branch_structure else (emp.branch_structure if emp else None)

            branch_name = None
            if struct and getattr(struct, 'branch', None):
                branch_name = (
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )

            sector_name = None
            if struct and getattr(struct, 'sector', None):
                sector_name = (
                    getattr(struct.sector, 'name_en', None) or 
                    getattr(struct.sector, 'sector_name', None) or 
                    getattr(struct.sector, 'name', None) or 
                    str(struct.sector)
                )

            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = (
                    getattr(struct.department, 'name_en', None) or 
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            asset_data = {
                "id": asset.id if asset else None,
                "serial_number": asset.serial_number if asset else None,
                "brand": asset.brand if asset else None,
                "model_or_pn": asset.model_or_pn if asset else None,
                "status": asset.status if asset else None,
                "category": {
                    "id": cat.id if cat else None,
                    "name_en": cat.name_en if cat else None,
                    "name_ar": cat.name_ar if cat else None,
                }
            }

            if cat and cat.name_en and cat.name_en.lower() in ['computer', 'pc', 'laptop']:
                specs_obj = getattr(asset, 'computerasset', None)
                
                if specs_obj:
                    asset_data["specs"] = {
                        "processor": getattr(specs_obj, 'processor', None),
                        "ram": getattr(specs_obj, 'memory_ram', None),
                        "storage": getattr(specs_obj, 'hard_disk', None),
                        "pc_type": getattr(specs_obj, 'pc_type', None),
                    }
                else:
                    asset_data["specs"] = "No specs recorded for this computer"

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                "asset_id": asset.id if asset else None,
                "employee": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "structure_id": struct.id if struct else None,
                    "assignment_type": "employee" if emp else "structure",
                    "branch_name": branch_name,
                    "sector_name": sector_name,
                    "department_name": department_name
                },
                "asset": asset_data
            })

        if page is not None and paginator is not None:
            return paginator.get_paginated_response(data)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignments_by_employee_code(request, emp_code):
    """
    API View to retrieve all active/past assignments for an employee with asset category.
    """
    # 🔒 Authorization Check
    if not request.user.has_perm('custody.view_consumercustody'):
        return Response(
            {"error": "You do not have permission to view employee assignments."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        assignments = ConsumerCustody.objects.filter(
            employee__employee_code=emp_code
        )
        
        serializer = CustodyAssignmentLookupSerializer(assignments, many=True)
        custom_data = serializer.data
        
        # Loop through the serialized results and manually inject the category string
        for index, assignment in enumerate(assignments):
            # Safe traversal: asset -> category -> category name field (e.g., name)
            if assignment.asset and hasattr(assignment.asset, 'category'):
                # Adjust '.name' to whatever field holds your category's string name (e.g., .name_en)
                category_name = assignment.asset.category.name if hasattr(assignment.asset.category, 'name') else str(assignment.asset.category)
                custom_data[index]['asset_category'] = category_name
            else:
                custom_data[index]['asset_category'] = None

        return Response(custom_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





import pandas as pd
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.organization.models import Branch, Sector, Department, BranchStructure
from apps.custody.models import Employee, ConsumerCustody
from apps.hardware_specs.models import ComputerAsset, BaseAsset, AssetCategory


def get_next_asset_code():
    """Fetches the last asset code numerically and increments it by 1."""
    # Annotate the queryset to treat the string as an integer for correct sorting
    last_asset = BaseAsset.objects.annotate(
        asset_code_int=Cast('asset_code', output_field=IntegerField())
    ).order_by('-asset_code_int').first()
    
    if last_asset and last_asset.asset_code and last_asset.asset_code.isdigit():
        return str(int(last_asset.asset_code) + 1)
    return "1"

def clean_val(row, idx):
    """Safely retrieves and cleans column values from a DataFrame row, removing float .0 suffixes."""
    if idx < len(row) and pd.notna(row[idx]):
        val = row[idx]
        
        if isinstance(val, float) and val.is_integer():
            val = int(val)
            
        val_str = str(val).strip()
        
        if val_str.endswith('.0'):
            val_str = val_str[:-2]
            
        return val_str if val_str.lower() != 'nan' and val_str != '' else None
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_computers_from_excel(request):
    file = request.FILES.get('file')
    
    # 1. Validate File Upload
    if not file:
        return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
    
    if not (file.name.endswith('.xls') or file.name.endswith('.xlsx')):
        return Response({"error": "Invalid file type. Please upload an Excel sheet (.xls, .xlsx)."}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Fetch or Create Required 'Computer' AssetCategory
    computer_category = AssetCategory.objects.filter(name_en__iexact="Computer").first()
    if not computer_category:
        computer_category = AssetCategory.objects.filter(id=8).first()
    if not computer_category:
        computer_category, _ = AssetCategory.objects.get_or_create(
            name_en="Computer",
            defaults={"name_ar": "حواسب وآلات حاسبة", "category_type": "base_asset", "code": "PC"}
        )

    try:
        # Read file with dtype=str to preserve exact codes and leading zeros
        df = pd.read_excel(file, sheet_name=0, header=None, skiprows=4, dtype=str)
        
        success_logs = []
        error_logs = []
        processed_serials_in_file = set()

        for index, row in df.iterrows():
            row_number = index + 5  # Offsets skipped headers and zero-based index

            try:
                with transaction.atomic():
                    # Extract Organization & Employee Data
                    branch_name = clean_val(row, 0)
                    sector_name = clean_val(row, 1)
                    dept_name   = clean_val(row, 2)
                    emp_code    = clean_val(row, 3)
                    emp_name    = clean_val(row, 4)

                    # 💡 FIX: Column 10 is index 9 (or 10 if 0-based), Column 12 is index 11 (or 12 if 0-based)
                    laptop_flag  =  clean_val(row, 7)
                    desktop_flag =  clean_val(row, 9)
                    
                    pc_type = None
                    if laptop_flag:
                        pc_type = "Laptop"
                    elif desktop_flag:
                        pc_type = "Desktop"
                    else:
                        # Fallback default to prevent database NOT NULL constraint failure
                        pc_type = "Desktop"

                    # Extract Core Hardware Specs
                    brand       = clean_val(row, 11)
                    model       = clean_val(row, 12)
                    serial_num  = clean_val(row, 13)
                    processor   = clean_val(row, 14)
                    memory      = clean_val(row, 15)
                    hard_disk   = clean_val(row, 16)

                    # Extract Accessories
                    mon_brand   = clean_val(row, 18)
                    mon_model   = clean_val(row, 19)
                    mon_inches  = clean_val(row, 20)
                    mon_serial  = clean_val(row, 21)

                    kb_brand    = clean_val(row, 24)
                    kb_model    = clean_val(row, 25)
                    kb_serial   = clean_val(row, 26)

                    ms_brand    = clean_val(row, 28)
                    ms_model    = clean_val(row, 29)
                    ms_serial   = clean_val(row, 30)

                    bag_brand   = clean_val(row, 32)
                    bag_desc    = clean_val(row, 33)

                    # 3. Validate Required Fields
                    if not serial_num:
                        error_logs.append(f"Row {row_number}: Skipped - Serial Number is missing.")
                        continue
                        
                    if not emp_code:
                        error_logs.append(f"Row {row_number}: Skipped - Employee Code is missing.")
                        continue

                    # 4. Duplicate Check within Same File
                    if serial_num in processed_serials_in_file:
                        error_logs.append(f"Row {row_number}: Skipped - Duplicate Serial Number '{serial_num}' found multiple times in this file.")
                        continue
                    
                    processed_serials_in_file.add(serial_num)

                    # 5. Database Duplicate Check
                    existing_base_asset = BaseAsset.objects.filter(serial_number=serial_num).first()
                    computer = None

                    if existing_base_asset:
                        if existing_base_asset.status == 'assigned':
                            error_logs.append(f"Row {row_number}: Skipped - Asset '{serial_num}' is already assigned to an employee.")
                            continue
                        elif existing_base_asset.status in ['maintenance', 'scrapped']:
                            status_display = existing_base_asset.get_status_display()
                            error_logs.append(f"Row {row_number}: Skipped - Asset '{serial_num}' cannot be assigned (Status: {status_display}).")
                            continue
                        
                        try:
                            computer = existing_base_asset.computerasset
                        except ComputerAsset.DoesNotExist:
                            error_logs.append(f"Row {row_number}: Skipped - Serial '{serial_num}' exists under a non-computer category.")
                            continue

                    # 6. Validate Organization Structure
                    branch = Branch.objects.filter(name_en=branch_name).first()
                    if not branch:
                        error_logs.append(f"Row {row_number}: Skipped - Branch '{branch_name}' does not exist.")
                        continue
                        
                    sector = Sector.objects.filter(sector_name=sector_name).first()
                    if not sector:
                        error_logs.append(f"Row {row_number}: Skipped - Sector '{sector_name}' does not exist.")
                        continue
                        
                    department = Department.objects.filter(name=dept_name).first()
                    if not department:
                        error_logs.append(f"Row {row_number}: Skipped - Department '{dept_name}' does not exist.")
                        continue

                    branch_struct, _ = BranchStructure.objects.get_or_create(
                        branch=branch,
                        sector=sector,
                        department=department
                    )

                    # 7. Get or Create Employee
                    employee, _ = Employee.objects.get_or_create(
                        employee_code=emp_code,
                        defaults={
                            'name_ar': emp_name,
                            'branch_structure': branch_struct
                        }
                    )

                    # 8. Create or Update Computer Asset
                    if computer:
                        computer.brand = brand or computer.brand
                        computer.model_or_pn = model or computer.model_or_pn
                        computer.pc_type = pc_type or computer.pc_type
                        computer.processor = processor or computer.processor
                        computer.memory_ram = memory or computer.memory_ram
                        computer.hard_disk = hard_disk or computer.hard_disk

                        computer.monitor_brand = mon_brand
                        computer.monitor_model = mon_model
                        computer.monitor_inches = mon_inches
                        computer.monitor_serial = mon_serial

                        computer.keyboard_brand = kb_brand
                        computer.keyboard_model = kb_model
                        computer.keyboard_serial = kb_serial

                        computer.mouse_brand = ms_brand
                        computer.mouse_model = ms_model
                        computer.mouse_serial = ms_serial

                        computer.bag_brand = bag_brand
                        computer.bag_model_or_description = bag_desc

                        if not computer.created_at:
                            computer.created_at = timezone.now()

                        computer.save()
                    else:
                        new_asset_code = get_next_asset_code()
                        computer = ComputerAsset.objects.create(
                            asset_code=new_asset_code,
                            category=computer_category,
                            pc_type=pc_type,
                            serial_number=serial_num,
                            brand=brand,
                            model_or_pn=model,
                            processor=processor,
                            memory_ram=memory,
                            hard_disk=hard_disk,
                            status='in_stock',
                            created_at=timezone.now(),
                            # Accessories
                            monitor_brand=mon_brand,
                            monitor_model=mon_model,
                            monitor_inches=mon_inches,
                            monitor_serial=mon_serial,
                            keyboard_brand=kb_brand,
                            keyboard_model=kb_model,
                            keyboard_serial=kb_serial,
                            mouse_brand=ms_brand,
                            mouse_model=ms_model,
                            mouse_serial=ms_serial,
                            bag_brand=bag_brand,
                            bag_model_or_description=bag_desc
                        )

                    # 9. Assign Custody
                    ConsumerCustody.objects.create(
                        asset=computer,
                        employee=employee,
                        branch_structure=None,
                        action_type='issue',
                        assignment_date=timezone.now().date(),
                        assigned_by=request.user if request.user.is_authenticated else None,
                        notes="Bulk imported and assigned via Excel"
                    )

                    computer.status = 'assigned'
                    if not computer.created_at:
                        computer.created_at = timezone.now()
                    computer.save()

                    success_logs.append(f"Row {row_number}: Successfully assigned Computer '{serial_num}' and accessories to Employee '{emp_code}'.")

            except Exception as row_error:
                error_logs.append(f"Row {row_number}: Skipped due to error - {str(row_error)}")
                continue

        return Response({
            "message": "File processing completed.",
            "success_count": len(success_logs),
            "error_count": len(error_logs),
            "success_logs": success_logs,
            "error_logs": error_logs
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Failed to process file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    