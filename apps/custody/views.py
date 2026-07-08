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
            # Automatic combination generation pattern
            lookup_filters = {
                'branch_id': branch_id, 
                'department_id': department_id
            }
            if sector_id:
                lookup_filters['sector_id'] = sector_id
                
            # This looks up the entry, or creates it automatically if missing
            structure_obj, created = BranchStructure.objects.get_or_create(**lookup_filters)
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
                "last_known_sector": struct.sector.sector_name if struct and struct.sector else None,
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


from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from apps.organization.models import BranchStructure  # تأكد من مسار الاستيراد الفعلي لديك

@api_view(['POST'])
def assign_asset_to_structure(request):
    """
    API view to issue an in-stock asset DIRECTLY to a Branch, Sector, or Department layout.
    """
    serial_number = request.data.get('serial_number')
    structure_id = request.data.get('structure_id')
    notes = request.data.get('notes', '')

    # 1️⃣ التحقق من إرسال البيانات المطلوبة كاملة
    if not serial_number or not structure_id:
        return Response(
            {"error": "Both 'serial_number' and 'structure_id' are required fields."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # 2️⃣ جلب الأصل والتحقق من أنه متوفر بالمخزن
            asset = BaseAsset.objects.get(serial_number=serial_number)
            
            if asset.status != 'in_stock':
                return Response(
                    {"error": f"Asset {serial_number} cannot be assigned. Current status is: {asset.get_status_display() or asset.status}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3️⃣ جلب الهيكل التنظيمي الموحد (المقر المستهدف)
            try:
                branch_structure = BranchStructure.objects.get(id=structure_id)
            except BranchStructure.DoesNotExist:
                return Response(
                    {"error": f"Organizational Structure with ID {structure_id} does not exist."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # 4️⃣ إنشاء سجل العهدة (مع ترك حقل الموظف فارغاً null لأنه صرف للمكان)
            ConsumerCustody.objects.create(
                asset=asset,
                employee=None,  # 🌟 عهدة مكانية عامة للمقر وليست لشخص
                branch_structure=branch_structure,
                action_type='issue',
                assignment_date=timezone.now().date(),
                assigned_by=request.user if request.user.is_authenticated else None,
                notes=notes
            )

            # 5️⃣ تحويل حالة الأصل إلى مصروف (assigned)
            asset.status = 'assigned'
            asset.save()

        return Response(
            {"message": f"Asset {serial_number} has been successfully assigned to structure layout ID {structure_id}."}, 
            status=status.HTTP_201_CREATED
        )

    except BaseAsset.DoesNotExist:
        return Response({"error": f"Asset with serial {serial_number} not found."}, status=status.HTTP_404_NOT_FOUND)
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



from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
# تأكد من استيراد الموديلات المعتادة (BaseAsset, ConsumerCustody)

@api_view(['POST'])
def replace_structure_asset(request):
    """
    API view to process immediate hardware swap transactions safely for structural layout custody (Branch/Sector/Department).
    """
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
def get_asset_history(request, serial_number):
    """
    API view to fetch the tracking log history for a SPECIFIC asset by its serial number.
    Supports both employee personal custody and structural layout assignment seamlessly.
    """
    try:
        # 🌟 التعديل: تصفية الـ select_related لتشمل الـ branch_structure المباشر والـ computerasset للمواصفات
        history = ConsumerCustody.objects.select_related(
            'asset', 
            'asset__category', 
            'asset__computerasset',  # جلب مواصفات الكمبيوتر لو وجدت في خطوة واحدة
            'employee__branch_structure', 
            'branch_structure',      # جلب الهيكل المباشر للعهدة المكانية
            'assigned_by'
        ).filter(asset__serial_number=serial_number).order_by('-created_at')

        report = []
        for log in history:
            emp = log.employee
            asset = log.asset
            cat = asset.category if asset else None
            
            # 💡 جلب الهيكل التنظيمي الفعال (سواء من الموظف أو من العهدة المكانية مباشرة)
            struct = log.branch_structure if log.branch_structure else (emp.branch_structure if emp else None)
            
            # 🛡️ Safe extraction لبيانات الهيكل الإداري بدون الحقول الملغاة
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                branch_name = getattr(struct.branch, 'name_en', None) or getattr(struct.branch, 'branch_name', None) or str(struct.branch)
                
            sector_name = None
            if struct and getattr(struct, 'sector', None):
                sector_name = getattr(struct.sector, 'sector_name', None) or getattr(struct.sector, 'sector_name', None) or str(struct.sector)
                    
                
            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = getattr(struct.department, 'name', None) or getattr(struct.department, 'name', None) or str(struct.department)

            # 📦 بناء بيانات الأصل الأساسية المتاحة
            asset_data = {
                "id": asset.id if asset else None,
                "category_name_en": cat.name_en if cat else None,
                "category_name_ar": cat.name_ar if cat else None,
                "brand": asset.brand if asset else None,
                "model_or_pn": asset.model_or_pn if asset else None,
                "serial_number": asset.serial_number if asset else None,
            }

            # 💻 إلحاق الـ Specs لو كان هذا السجل يخص جهاز كمبيوتر في تاريخه
            if cat and cat.name_en.lower() in ['computer', 'pc', 'laptop']:
                comp_specs = getattr(asset, 'computerasset', None)
                if comp_specs:
                    asset_data["specs"] = {
                        "processor": getattr(comp_specs, 'processor', None),
                        "ram": getattr(comp_specs, 'ram', None),
                        "storage": getattr(comp_specs, 'storage', None),
                        "os": getattr(comp_specs, 'os', None),
                    }

            # تجميع الـ Log Item
            report.append({
                "custody_id": log.id,
                "action_type": log.action_type,
                "action_display": log.get_action_type_display() if hasattr(log, 'get_action_type_display') else log.action_type,
                "action_date": log.assignment_date,
                "return_date": log.return_date,
                
                # الكيان المستهلك: قد يكون موظفاً أو مقراً إدارياً
                "assignment_target": {
                    "type": "employee" if emp else "structure",
                    "structure_id": struct.id if struct else None,
                    "branch_name": branch_name,
                    "sector_name":sector_name,
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
def get_global_custody_history(request):
    """
    API view to fetch the complete tracking log history for ALL assets and consumers.
    Optimized performance to handle both employee personal custody and direct structural layouts,
    explicitly including tracking duration timelines.
    """
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
                branch_name = (
                    getattr(struct.sector, 'sector_name', None) or 
                    getattr(struct.sector, 'sector_name', None) or 
                    getattr(struct.sector, 'name', None) or 
                    str(struct.sector)
                )
            # Safe extraction for Department Name
            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = (
                    getattr(struct.department, 'name_en', None) or 
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
                    "sector_name":sector_name,
                    "department_name": department_name,
                    "employee_details": {
                        "employee_code": emp.employee_code,
                        "name_ar": emp.name_ar,
                        "name_en": emp.name_en,
                    } if emp else None
                },
                
                "asset_details": {
                    "id": asset.id if asset else None,
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
def get_all_active_assignments(request):
    """
    API view to get all currently assigned hardware assets and the entities holding them.
    Filters out returned assets (return_date IS NULL) and supports both employee and direct structural custody.
    """
    try:
        # 🌟 التعديل الجوهري: عمل JOIN يغطي الـ branch_structure المباشر والـ branch_structure التابع للموظف معاً
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset',
            'employee__branch_structure',
            'branch_structure'  # جلب الهيكل التنظيمي المباشر في حال كانت عهدة مكانية
        ).order_by('-assignment_date')

        data = []
        for custody in active_assignments:
            emp = custody.employee
            asset = custody.asset
            
            # 💡 جلب الهيكل التنظيمي الفعال: إما المباشر من العهدة أو المشتق من الموظف
            struct = custody.branch_structure if custody.branch_structure else (emp.branch_structure if emp else None)
            
            # 🛡️ استخراج اسم الفرع بأمان (Safe Extraction)
            branch_name = None
            if struct and getattr(struct, 'branch', None):
                branch_name = (
                    getattr(struct.branch, 'name_en', None) or 
                    getattr(struct.branch, 'branch_name', None) or 
                    getattr(struct.branch, 'name', None) or 
                    str(struct.branch)
                )
            sector_name =None
            if struct and getattr(struct, 'sector', None):
                sector_name = (
                    getattr(struct.sector, 'sector_name', None) or 
                    getattr(struct.sector, 'name', None) or 
                    getattr(struct.sector, 'sec_name', None) or 
                    str(struct.secor)
                )    
            # 🛡️ استخراج اسم القسم بأمان (Safe Extraction)
            department_name = None
            if struct and getattr(struct, 'department', None):
                department_name = (
                    getattr(struct.department, 'name_en', None) or 
                    getattr(struct.department, 'department_name', None) or 
                    getattr(struct.department, 'name', None) or 
                    str(struct.department)
                )

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                
                # إرجاع بيانات الـ Consumer مع ملء بيانات الفرع والقسم ديناميكياً سواء كان هناك موظف أم لا
                "employee": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "branch": branch_name,
                    "sector":sector_name,
                    "department": department_name,
                    "assignment_type": "employee" if emp else "structure"  # الراية دي بتعرف الفرونت إند نوع العهدة فوراً
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
    API view to get all currently assigned hardware assets filtered by category name.
    Supports both employee custody and direct structural layout assignment securely.
    """
    category_name = request.query_params.get('name', None)
    
    if not category_name:
        return Response(
            {"error": "Please provide a 'name' parameter (e.g., ?name=pc)"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 🌟 التعديل الأساسي: تحسين الـ JOIN ليشمل الهيكل المباشر وعلاقة مواصفات الحاسوب
        active_assignments = ConsumerCustody.objects.filter(
            action_type='issue',
            return_date__isnull=True
        ).select_related(
            'asset__category', 
            'asset__computerasset',  # جلب المواصفات في خطوة واحدة لو كان كمبيوتر
            'employee__branch_structure',
            'branch_structure'       # جلب الهيكل المباشر للعهدة المكانية
        ).filter(
            Q(asset__category__name_en__icontains=category_name) | 
            Q(asset__category__name_ar__icontains=category_name)
        ).order_by('-assignment_date')

        data = []
        for custody in active_assignments:
            emp = custody.employee
            asset = custody.asset
            cat = asset.category if asset else None
            
            # 💡 جلب الهيكل التنظيمي الفعال (مباشر أو من خلال الموظف) بشكل آمن لمنع الكراش
            struct = custody.branch_structure if custody.branch_structure else (emp.branch_structure if emp else None)

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

            # 💻 جلب مواصفات الحاسوب بشكل آمن وموحد
            if cat and cat.name_en.lower() in ['computer', 'pc', 'laptop']:
                specs_obj = getattr(asset, 'computerasset', None) or getattr(asset, 'specs', None) or getattr(asset, 'computerspecs', None)
                
                if specs_obj:
                    asset_data["specs"] = {
                        "processor": getattr(specs_obj, 'processor', None),
                        "ram": getattr(specs_obj, 'ram', None),
                        "storage": getattr(specs_obj, 'storage', None),
                        "os": getattr(specs_obj, 'os', None),
                    }
                else:
                    asset_data["specs"] = "No specs recorded for this computer"

            data.append({
                "assignment_id": custody.id,
                "assignment_date": custody.assignment_date,
                "notes": custody.notes,
                "employee": {
                    "employee_code": emp.employee_code if emp else None,
                    "name_en": emp.name_en if emp else None,
                    "name_ar": emp.name_ar if emp else None,
                    "structure_id": struct.id if struct else None,
                    "assignment_type": "employee" if emp else "structure"  # راية توضيحية للفرونت إند
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
    Looks up who or what branch layout currently holds custody of a device by its serial number.
    Supports both live employee custody and direct structural branch framework assignments.
    """
    try:
        # 1️⃣ التحقق من وجود الأصل أولاً مع عمل Join للفئة لمنع الاستعلامات المتكررة
        asset = BaseAsset.objects.select_related('category').get(serial_number=serial_number)
    except BaseAsset.DoesNotExist:
        return Response({"error": f"Device with serial number '{serial_number}' not found."}, status=status.HTTP_404_NOT_FOUND)

    # 2️⃣ جلب العهدة النشطة الحالية فقط (التي لم تُسترد بعد)
    active_custody = ConsumerCustody.objects.select_related(
        'employee__branch_structure',
        'branch_structure'
    ).filter(
        asset=asset,
        action_type='issue',
        return_date__isnull=True
    ).order_by('-created_at').first()

    # 💡 بناء تفاصيل الجهاز الأساسية لإرجاعها في كلتا الحالتين
    device_details = {
        "id": asset.id,
        "serial_number": asset.serial_number,
        "brand": asset.brand,
        "model_or_pn": asset.model_or_pn,
        "status": asset.status,
        "category_name": asset.category.name_en if asset.category else None
    }

    # 3️⃣ إذا لم توجد عهدة نشطة، أو لم يرتبط بها موظف ولا هيكل تنظيمي، فالجهاز متاح بالمخزن
    if not active_custody or (not active_custody.employee and not active_custody.branch_structure):
        return Response({
            "message": "Device exists and is currently available in stock.",
            "custody_status": "in_stock",
            "device_details": device_details
        }, status=status.HTTP_200_OK)

    # 4️⃣ جلب الهيكل التنظيمي الفعال بأمان (من العهدة مباشرة أو من الموظف)
    struct = active_custody.branch_structure if active_custody.branch_structure else (active_custody.employee.branch_structure if active_custody.employee else None)
    
    branch_name = None
    if struct and getattr(struct, 'branch', None):
        branch_name = getattr(struct.branch, 'name_en', None) or getattr(struct.branch, 'branch_name', None) or str(struct.branch)
     
    sector_name = None
    if struct and getattr(struct, 'sector', None):
        sector_name = getattr(struct.sector, 'sector_name', None) or getattr(struct.branch, 'sector_name', None) or str(struct.sector)
     
        
    department_name = None
    if struct and getattr(struct, 'department', None):
        department_name = getattr(struct.department, 'name', None) or getattr(struct.department, 'name', None) or str(struct.department)

    # 5️⃣ تشكيل الـ Response النهائي ليتناسب مع React بدون الاعتماد الكلي على السيريالايزر القديم المقيد بالموظف
    return Response({
        "message": "Device is currently deployed.",
        "custody_status": "assigned",
        "assignment_details": {
            "custody_id": active_custody.id,
            "assignment_date": active_custody.assignment_date,
            "assignment_type": "employee" if active_custody.employee else "structure",
            "notes": active_custody.notes,
            "location": {
                "structure_id": struct.id if struct else None,
                "branch_name": branch_name,
                "sector_name": sector_name,
                "department_name": department_name,
            },
            "employee_details": {
                "employee_code": active_custody.employee.employee_code,
                "name_en": active_custody.employee.name_en,
                "name_ar": active_custody.employee.name_ar,
            } if active_custody.employee else None
        },
        "device_details": device_details
    }, status=status.HTTP_200_OK)
    
    
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import CustodyAssignmentLookupSerializer # Replace with your actual Serializer name

@api_view(['GET'])
def get_assignments_by_employee_code(request, emp_code):
    """
    API View to retrieve all active/past assignments for an employee with asset category.
    """
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