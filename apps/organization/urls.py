from django.urls import path
from . import views

app_name = 'organization'

urlpatterns = [
    # ==========================================
    # 🏢 Branches Endpoints
    # ==========================================
    path('branches/', views.branch_list, name='branch_list'),
    path('branches/<int:pk>/', views.branch_detail, name='branch_detail'),
    path('branches/update/<int:branch_id>/', views.update_branch, name='update-branch'),
    path('branches/<int:branch_id>/sectors/', views.sectors_by_branch, name='sectors_by_branch'),

    # ==========================================
    # 📊 Sectors Endpoints
    # ==========================================
    path('sectors/', views.sector_list, name='sector_list'),
    path('sectors/<int:pk>/', views.sector_detail, name='sector_detail'),

    # ==========================================
    # 🗂️ Departments Endpoints
    # ==========================================
    path('branches/<int:branch_id>/sectors/<int:sector_id>/departments/', views.department_list, name='department_list_create'),
    
    # الروابط العامة للأقسام والتعديل/الحذف
    path('departments/', views.department_list, name='department_list'), 
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),

    # ==========================================
    # 🌟 Branch Structure Endpoints (الهيكل الموحد)
    # ==========================================
    path('structures/', views.branch_structure_list, name='branch_structure_list'),
    path('structures/<int:pk>/', views.branch_structure_detail, name='branch_structure_detail'),
]