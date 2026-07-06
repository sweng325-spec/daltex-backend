from django.urls import path
from . import views

urlpatterns = [
    path('stock/', views.inventory_list_create, name='inventory-list-create'),
    path('stock/<int:pk>/', views.inventory_detail_update_delete, name='inventory-detail-update-delete'),
    
    # 🔄 Stock Balance Adjustments (Increases / Decreases)
    path('stock/adjust/<int:pk>/', views.adjust_accessory_stock, name='adjust-accessory-stock'),
    
    path('history/', views.inventory_history_list, name='inventory-history-list'),
    
]