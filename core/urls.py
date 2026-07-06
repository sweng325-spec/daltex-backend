from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # مسار لوحة تحكم دجانغو الافتراضية
    path('admin/', admin.site.urls),
    
    # 🌟 ربط مسارات الهيكل التنظيمي للمشروع

    # 🔌 ربط مسارات الـ APIs الخاصة بالأصول والمواصفات بالـ core تلقائياً
    path('api/', include('apps.hardware_specs.urls')), 
    path('api/org/', include('apps.organization.urls', namespace='organization')),
    path('api/custody/', include('apps.custody.urls')), 
    path('api/inventory/', include('apps.inventory.urls')),
]