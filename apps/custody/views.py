from django.db import transaction
from django.utils import timezone
from django.db.models import Max
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from apps.hardware_specs.models import BaseAsset
from .models import ConsumerCustody, Employee
from apps.organization.models import BranchStructure
from apps.hardware_specs.models import BaseAsset
###########################################################
## Custody Management API Views
###########################################################
@api_view(['POST'])
def add_new_employee(request):
    """
    API view to register a new unique employee tied to the consolidated BranchStructure.
    """
    try:
        emp_code = request.data.get('employee_code')
        name_ar = request.data.get('employee_name_ar')
        name_en = request.data.get('employee_name_en')
        email = request.data.get('email') # استقبال الحقل الجديد المضاف
        
        # استقبال معطيات الهيكل الإداري
        branch_id = request.data.get('branch_id')
        sector_id = request.data.get('sector_id')  # يفضل إرساله من الفرونت إند لضمان دقة التوليفة
        department_id = request.data.get('department_id')
        
        # 🌟 أو استقبال المعرّف المباشر إذا كان الفرونت إند يرسله جاهزاً
        branch_structure_id = request.data.get('branch_structure_id')

        if not emp_code or not name_ar:
            return Response(
                {"error": "employee_code and employee_name_ar are required fields."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if Employee.objects.filter(employee_code=emp_code).exists():
            return Response(
                {"error": f"Employee with code '{emp_code}' already exists."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # تحديد الـ BranchStructure المستهدف للموظف
        structure_obj = None
        
        if branch_structure_id:
            try:
                structure_obj = BranchStructure.objects.get(id=branch_structure_id)
            except BranchStructure.DoesNotExist:
                return Response({"error": "Selected branch_structure_id does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        
        elif branch_id and department_id:
            # محاولة البحث عن التوليفة الهيكلية المطابقة في قاعدة البيانات
            lookup_filters = {'branch_id': branch_id, 'department_id': department_id}
            if sector_id:
                lookup_filters['sector_id'] = sector_id
                
            structure_obj = BranchStructure.objects.filter(**lookup_filters).first()
            
            if not structure_obj:
                return Response(
                    {"error": "The specified organizational structure (Branch/Sector/Department combo) does not exist. Please link them first."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 🌟 إنشاء الموظف الجديد مع ربطه بالهيكل الصحيح
        new_emp = Employee.objects.create(
            employee_code=emp_code,
            name_ar=name_ar,
            name_en=name_en if name_en else "",
            email=email,
            branch_structure=structure_obj # إسناد كائن الهيكل الموحد الجديد
        )

        return Response({
            "message": "Employee recorded successfully.",
            "employee_code": new_emp.employee_code
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
@api_view(['GET'])
def unique_employee_list(request):
    """
    API view to fetch all employees from the independent master table 
    with their consolidated branch and department details.
    """
    try:
        # 🌟 التعديل هنا: الوصول للعلاقات المبطنة عبر جدول الهيكل الموحد
        employees = Employee.objects.select_related(
            'branch_structure__branch', 
            'branch_structure__department'
        ).all().order_by('name_en')
        
        employee_list = []
        for emp in employees:
            # التحقق من وجود هيكل تنظيمي مربوط بالموظف لتجنب الـ AttributeError
            struct = emp.branch_structure
            
            employee_list.append({
                "employee_code": emp.employee_code,
                "employee_name_ar": emp.name_ar,
                "employee_name_en": emp.name_en,
                # 🌟 جلب البيانات من جدول الربط المركزي الموحد
                "last_known_branch": struct.branch.name_en if struct and struct.branch else None,
                "last_known_department": struct.department.name if struct and struct.department else None,
            })

        return Response(employee_list, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)@api_view(['GET'])
    
@api_view(['GET'])
def get_employee_by_code(request, employee_code):
    """
    API view to retrieve a single employee's profile by their unique employee_code.
    Safely handles dynamic branch and department naming fields via the consolidated structure.
    """
    try:
        # 🌟 استخدام select_related لجلب العلاقات المبطنة من جدول الربط المركزي الموحد
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
            "email": employee.email,  # جلب الإيميل الجديد المضاف في الموديل
            "last_known_branch": branch_name,
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
def delete_employee(request, employee_code):
    """
    API view to safely delete an employee by their unique code.
    Blocks deletion if the employee holds active asset custody.
    """
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
def update_employee(request, employee_code):
    """
    API view to update an existing employee's fields.
    Supports updating personal info and migrating to a new BranchStructure.
    """
    try:
        # جلب الموظف مع علاقاته الحالية
        employee = Employee.objects.select_related('branch_structure').get(employee_code=employee_code)
        
        # 1️⃣ تحديث البيانات النصية الشخصية (إذا تم إرسالها)
        if 'name_ar' in request.data:
            employee.name_ar = request.data['name_ar']
        if 'name_en' in request.data:
            employee.name_en = request.data['name_en']
        if 'email' in request.data:
            employee.email = request.data['email']
            
        # 2️⃣ التعامل مع تحديثات الهيكل الإداري (Organizational Structure)
        structure_id = request.data.get('structure_id')
        
        if structure_id:
            # حالة أ: الفرونت إند أرسل معرف الهيكل الجديد مباشرة
            try:
                structure_obj = BranchStructure.objects.get(id=structure_id)
                employee.branch_structure = structure_obj
            except BranchStructure.DoesNotExist:
                return Response({"error": f"BranchStructure with ID '{structure_id}' does not exist."}, status=status.HTTP_404_NOT_FOUND)
                
        elif any(k in request.data for k in ['branch_id', 'sector_id', 'department_id']):
            # حالة ب: الفرونت إند أرسل معرفات منفصلة، نقوم ببناء فلتر ديناميكي للبحث
            current_struct = employee.branch_structure
            
            # نأخذ القيم الجديدة من الـ request، وإذا لم ترسل نعتمد على القيم الحالية للموظف كـ fallback
            branch_id = request.data.get('branch_id') or (current_struct.branch_id if current_struct else None)
            sector_id = request.data.get('sector_id') or (current_struct.sector_id if current_struct else None)
            department_id = request.data.get('department_id') or (current_struct.department_id if current_struct else None)
            
            if not branch_id or not department_id:
                return Response(
                    {"error": "Both branch_id and department_id must be determinable to resolve the target structure."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # البحث عن التوليفة الهيكلية المطابقة
            lookup_filters = {'branch_id': branch_id, 'department_id': department_id}
            if sector_id:
                lookup_filters['sector_id'] = sector_id
                
            structure_obj = BranchStructure.objects.filter(**lookup_filters).first()
            
            if not structure_obj:
                return Response(
                    {"error": "The specified combination of Branch, Sector, and Department does not exist in BranchStructure registry."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            employee.branch_structure = structure_obj
            
        # حفظ التعديلات في قاعدة البيانات
        employee.save()
        
        # تحضير الـ Response بالبيانات الجديدة
        struct = employee.branch_structure
        return Response({
            "message": f"Employee {employee_code} updated successfully.",
            "employee": {
                "employee_code": employee.employee_code,
                "name_ar": employee.name_ar,
                "name_en": employee.name_en,
                "email": employee.email,
                "structure_id": struct.id if struct else None,
                "branch_id": struct.branch_id if struct else None,
                "sector_id": struct.sector_id if struct else None,
                "department_id": struct.department_id if struct else None,
            }
        }, status=status.HTTP_200_OK)
        
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
############################################################################
## Asset Assignment API Views
############################################################################
@api_view(['POST'])
def assign_asset_custody(request):
    """
    API view to issue an in-stock asset to an employee using their unique code.
    """
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

        return Response({"message": f"Asset {serial_number} successfully assigned to employee {employee_code}."}, status=status.HTTP_201_CREATED)

    except BaseAsset.DoesNotExist:
        return Response({"error": f"Asset with serial {serial_number} not found."}, status=status.HTTP_404_NOT_FOUND)
    except Employee.DoesNotExist:
        return Response({"error": f"Employee with code {employee_code} not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def replace_consumer_asset(request):
    """
    API view to process immediate hardware swap transactions safely.
    """
    old_serial = request.data.get('old_serial_number')
    new_serial = request.data.get('new_serial_number')
    notes = request.data.get('notes', 'Swapped via hardware replacement desk.')
    it_technician = request.user if request.user.is_authenticated else None

    if not old_serial or not new_serial:
        return Response({"error": "Both old and new serial numbers are mandatory."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            old_asset = BaseAsset.objects.get(serial_number=old_serial)
            new_asset = BaseAsset.objects.get(serial_number=new_serial)

            if new_asset.status != 'in_stock':
                return Response({"error": f"Target replacement asset {new_serial} is not in stock"}, status=status.HTTP_400_BAD_REQUEST)

            active_custody = old_asset.custody_history.filter(action_type='issue', return_date__isnull=True).first()
            if not active_custody:
                return Response({"error": f"No active custody trace available for asset {old_serial}"}, status=status.HTTP_400_BAD_REQUEST)

            current_date = timezone.now().date()

            active_custody.return_date = current_date
            active_custody.notes = f"Closed: Swapped with asset S/N: {new_serial}. Details: {notes}"
            active_custody.save()

            ConsumerCustody.objects.create(
                asset=old_asset,
                employee=active_custody.employee,
                action_type='return',
                assignment_date=current_date,
                assigned_by=it_technician,
                notes=request.notes if hasattr(request, 'notes') else f"Returned automatically due to replacement with asset S/N: {new_serial}"
            )
            
            old_asset.status = 'maintenance'
            old_asset.save()

            ConsumerCustody.objects.create(
                asset=new_asset,
                employee=active_custody.employee,
                action_type='issue',
                assignment_date=current_date,
                assigned_by=it_technician,
                notes=f"Issued automatically to replace asset S/N: {old_serial}"
            )

            new_asset.status = 'assigned'
            new_asset.save()

        return Response({"message": "Hardware replacement log committed successfully."}, status=status.HTTP_200_OK)

    except BaseAsset.DoesNotExist:
        return Response({"error": "Failed to map requested serial numbers to existing objects."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_asset_history(request, serial_number):
    """
    API view to fetch the tracking log history for a SPECIFIC asset by its serial number.
    Updates relationships to comply with the new branch_structure framework.
    """
    try:
        # 🌟 التعديل هنا: تصحيح الـ select_related ليمر بالهيكل الإداري الجديد للموظف
        history = ConsumerCustody.objects.select_related(
            'asset', 
            'asset__category', 
            'employee__branch_structure__branch', 
            'employee__branch_structure__department', 
            'assigned_by'
        ).filter(asset__serial_number=serial_number).order_by('-created_at')

        report = []
        for log in history:
            emp = log.employee
            struct = emp.branch_structure if emp else None
            
            # 🛡️ Safe extraction لاسم الفرع
            branch_name = None
            if struct and struct.branch:
                branch_name = (
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )
            
            # 🛡️ Safe extraction لاسم القسم
            department_name = None
            if struct and struct.department:
                department_name = (
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name_en', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            report.append({
                "custody_id": log.id,
                "action_type": log.action_type,
                "action_display": log.get_action_type_display(),
                "action_date": log.assignment_date,
                "return_date": log.return_date,
                
                "consumer": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "branch_name": branch_name,
                    "department_name": department_name,
                },
                
                "asset": {
                    "id": log.asset.id if log.asset else None,
                    "category_name_en": log.asset.category.name_en if log.asset and log.asset.category else None,
                    "category_name_ar": log.asset.category.name_ar if log.asset and log.asset.category else None,
                    "brand": log.asset.brand if log.asset else None,
                    "model_or_pn": log.asset.model_or_pn if log.asset else None,
                    "serial_number": log.asset.serial_number if log.asset else None,
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
def get_global_custody_history(request):
    """
    API view to fetch the complete tracking log history for ALL assets and consumers.
    Supports the consolidated organizational structure framework.
    """
    try:
        # 🌟 التعديل الأساسي: ربط الـ JOIN المتداخل ليمر عبر branch_structure
        global_history = ConsumerCustody.objects.select_related(
            'asset', 
            'asset__category', 
            'employee__branch_structure__branch', 
            'employee__branch_structure__department', 
            'assigned_by'
        ).all().order_by('-created_at')

        report = []
        for log in global_history:
            emp = log.employee
            struct = emp.branch_structure if emp else None
            
            # 🛡️ استخراج اسم الفرع بأمان
            branch_name = None
            if struct and struct.branch:
                branch_name = (
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )
            
            # 🛡️ استخراج اسم القسم بأمان
            department_name = None
            if struct and struct.department:
                department_name = (
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name_en', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            report.append({
                "custody_id": log.id,
                "action_type": log.action_type,
                "action_display": log.get_action_type_display(),
                "action_date": log.assignment_date,
                "return_date": log.return_date,
                
                "consumer": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "branch_name": branch_name,
                    "department_name": department_name,
                },
                
                "asset": {
                    "id": log.asset.id if log.asset else None,
                    "category_name_en": log.asset.category.name_en if log.asset and log.asset.category else None,
                    "category_name_ar": log.asset.category.name_ar if log.asset and log.asset.category else None,
                    "brand": log.asset.brand if log.asset else None,
                    "model_or_pn": log.asset.model_or_pn if log.asset else None,
                    "serial_number": log.asset.serial_number if log.asset else None,
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
def get_all_active_assignments(request):
    """
    API view to get all currently assigned hardware assets and the employees holding them.
    Filters out returned assets (return_date IS NULL) and supports the consolidated structural framework.
    """
    try:
        # Fetch only active issuances
        # 🌟 التعديل هنا: استخدام العلاقات المبطنة عبر الـ branch_structure التابع للموظف
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset',
            'employee__branch_structure__branch',
            'employee__branch_structure__department'
        ).order_by('-assignment_date')

        data = []
        for custody in active_assignments:
            emp = custody.employee
            asset = custody.asset
            
            # استخراج الهيكل التنظيمي المربوط بالموظف بأمان
            struct = emp.branch_structure if emp else None
            
            # 🛡️ Safe fallbacks for branch and department names via branch_structure
            branch_name = None
            if struct and struct.branch:
                branch_name = (
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )
                
            department_name = None
            if struct and struct.department:
                department_name = (
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name_en', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                "employee": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "branch": branch_name,
                    "department": department_name
                },
                "asset": {
                    "id": asset.id if asset else None,
                    "serial_number": asset.serial_number if asset else None,
                    "brand": asset.brand if asset else None,
                    "model_or_pn": asset.model_or_pn if asset else None,
                    "status": asset.status if asset else None
                }
            })

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
 
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import ConsumerCustody

@api_view(['GET'])
def get_assigned_assets_by_category(request):
    """
    جلب العهد النشطة مفلترة حسب اسم التصنيف.
    تعتمد بالكامل على الـ branch_structure_id وتتجنب تماماً الحقول الملغاة.
    الرابط: /api/custody/assets/by-category/?name=pc
    """
    category_name = request.query_params.get('name', None)
    
    if not category_name:
        return Response(
            {"error": "Please provide a 'name' parameter (e.g., ?name=pc)"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 🌟 الاعتماد الحصري على branch_structure وجلب الـ ID الخاص به مباشرة
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset__category', 
            'employee__branch_structure'
        ).filter(
            Q(asset__category__name_en__icontains=category_name) | 
            Q(asset__category__name_ar__icontains=category_name)
        ).order_by('-assignment_date')

        data = []
        for custody in active_assignments:
            emp = custody.employee
            asset = custody.asset
            cat = asset.category if asset else None
            struct = emp.branch_structure if emp else None

            # 📦 بناء كائن بيانات الأصل الأساسية المتاحة في BaseAsset
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

            # 💻 الفحص الديناميكي: لو التصنيف يخص الكمبيوتر، ألحق المواصفات فوراً
            if cat and cat.name_en.lower() in ['computer', 'pc', 'laptop']:
                specs_obj = getattr(asset, 'specs', None) or getattr(asset, 'computerspecs', None)
                
                if specs_obj:
                    asset_data["specs"] = {
                        "processor": getattr(specs_obj, 'processor', None),
                        "ram": getattr(specs_obj, 'ram', None),
                        "storage": getattr(specs_obj, 'storage', None),
                        "os": getattr(specs_obj, 'os', None),
                    }
                else:
                    asset_data["specs"] = "No specs recorded for this computer"

            # تجميع البيانات وإرجاع الـ structure_id للموظف دون تفصيل الحقول المحذوفة
            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                "employee": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "structure_id": struct.id if struct else None  # 🌟 تم استبدال الـ branch والـ department بالـ ID الموحد هنا
                },
                "asset": asset_data
            })

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
 
         
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from apps.hardware_specs.models import BaseAsset
from .models import ConsumerCustody
from .serializers import CustodyAssignmentLookupSerializer

@api_view(['GET'])
def get_custody_by_serial(request, serial_number):
    """
    Looks up who currently holds custody of a device by its serial number.
    """
    try:
        # 1. Locate the physical hardware asset
        asset = BaseAsset.objects.get(serial_number=serial_number)
    except BaseAsset.DoesNotExist:
        return Response({"error": f"Device with serial number '{serial_number}' not found."}, status=status.HTTP_404_NOT_FOUND)

    # 2. Grab the active custody record for this machine
    # Filtering for 'delivered' or active states depending on your business rules
    custody_record = ConsumerCustody.objects.filter(asset=asset).order_by('-id').first()

    if not custody_record or not custody_record.employee:
        return Response({
            "message": "Device exists but is currently unassigned.",
            "device_details": {
                "serial_number": asset.serial_number,
                "brand": asset.brand,
                "model_or_pn": asset.model_or_pn,
                "status": asset.status # Expected to be 'in_stock'
            }
        }, status=status.HTTP_200_OK)

    # 3. Serialize and return the matched combined layout
    serializer = CustodyAssignmentLookupSerializer(custody_record)
    return Response(serializer.data, status=status.HTTP_200_OK)