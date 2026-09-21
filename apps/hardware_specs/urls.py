from django.urls import path
from . import views

app_name = 'hardware_specs'

urlpatterns = [
    # 1️⃣ Hardware Assets CRUD
    path('hardware-assets/', views.hardware_asset_list, name='hardware_asset_list'),
    path('hardware-assets/maintenance/', views.maintenance_assets_by_category, name='maintenance-assets-by-category'),  
    path('hardware-assets/<str:pk>/', views.hardware_asset_detail, name='hardware_asset_detail'),

    # 2️⃣ Printers Specs CRUD
    path('printers/', views.printer_list, name='printer_list'),
    path('printers/<str:pk>/', views.printer_detail, name='printer_detail'),
    
    # 3️⃣ Computers CRUD
    path('computers/', views.computer_list, name='computer_list'),
    path('computers/<str:pk>/', views.computer_detail, name='computer_detail'),
    path('computers/type/<str:pc_type>/', views.computer_list_by_type, name='computer_list_by_type'),
    
    # 4️⃣ Tablets CRUD
    path('tablets/', views.tablet_list, name='tablet_list'),
    path('tablets/<str:pk>/', views.tablet_detail, name='tablet_detail'),
    
    # 5️⃣ Categories CRUD Operations
    path('categories/all/', views.get_all_categories, name='get_all_categories'),
    path('categories/spare-parts/', views.get_spare_parts_categories, name='get_spare_parts_categories'),
    path('categories/base-assets/', views.get_base_asset_categories, name='get-base-asset-categories'),
    path('categories/accessories/', views.get_accessory_categories, name='get-accessory-categories'),
    path('categories/add/', views.post_new_category, name='post-new-category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete-category'),
    
    # 6️⃣ Monitors CRUD Operations
    path('monitors/', views.monitor_list_create, name='monitor-list-create'),
    path('monitors/<str:pk>/', views.monitor_detail_update_delete, name='monitor-detail-update-delete'),

    path('assets/in-stock/', views.get_in_stock_assets_by_category, name='get_in_stock_assets_by_category'),
    path('in-stock-count/', views.hardware_asset_instock_count, name='hardware-asset-instock-count'),
]