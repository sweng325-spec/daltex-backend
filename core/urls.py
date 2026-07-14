from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import CustomTokenObtainPairView  # 👈 Import your new custom view
from rest_framework_simplejwt.views import TokenRefreshView
from .views import get_user_permissions


urlpatterns = [
    # مسار لوحة تحكم دجانغو الافتراضية
    path('admin/', admin.site.urls),
    
    # 🌟 ربط مسارات الهيكل التنظيمي للمشروع

    # 🔌 ربط مسارات الـ APIs الخاصة بالأصول والمواصفات بالـ core تلقائياً
    path('api/', include('apps.hardware_specs.urls')), 
    path('api/org/', include('apps.organization.urls', namespace='organization')),
    path('api/custody/', include('apps.custody.urls')), 
    path('api/inventory/', include('apps.inventory.urls')),
    
    
    
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # 🔄 Endpoint to get a new Access token using the Refresh token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('api/user/permissions/', get_user_permissions, name='user_permissions'),
]