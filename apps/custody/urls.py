from django.urls import path
from . import views

urlpatterns = [
    # Master Employee Records
    path('employees/', views.unique_employee_list, name='unique-employee-list'),
    path('employees/add/', views.add_new_employee, name='add-new-employee'),
    path('employees/<str:employee_code>/', views.get_employee_by_code, name='get-employee-by-code'),
    path('employees/delete/<str:employee_code>/', views.delete_employee, name='delete-employee'),
    path('employees/update/<str:employee_code>/', views.update_employee, name='update-employee'),
    
    # Asset Custody Operational Flow
    path('assign/', views.assign_asset_custody, name='assign-asset-custody'),
    path('replace/', views.replace_consumer_asset, name='replace-consumer-asset'),
    path('lookup/<str:serial_number>/', views.get_custody_by_serial, name='custody-lookup-by-serial'),
    
    # History Trails and Logging Analytics
    path('history/global/', views.get_global_custody_history, name='get-global-custody-history'),
    path('history/asset/<str:serial_number>/', views.get_asset_history, name='get-asset-history'),
    
    path('assignments/active/', views.get_all_active_assignments, name='get-all-active-assignments'),
    path('assets/by-category/', views.get_assigned_assets_by_category, name='get_assigned_assets_by_category'),

]