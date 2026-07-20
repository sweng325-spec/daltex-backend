from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import CustomTokenObtainPairView  # 👈 Import your new custom view
from .import views
from .views import get_user_permissions


urlpatterns = [
    
    path('admin/', admin.site.urls),
    
   


    path('api/', include('apps.hardware_specs.urls')), 
    path('api/org/', include('apps.organization.urls', namespace='organization')),
    path('api/custody/', include('apps.custody.urls')), 
    path('api/inventory/', include('apps.inventory.urls')),
    
    
    
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # 🔄 Endpoint to get a new Access token using the Refresh token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('api/user/permissions/', get_user_permissions, name='user_permissions'),
    path('auth/change-password/', views.change_password, name='change-password'),
    path('auth/register/', views.create_user_with_group, name='register-user-with-group'),
    path('auth/groups/', views.list_groups, name='list-groups'),
    path('auth/users/', views.list_users_with_groups, name='list-users-with-groups'),
    path('auth/users/<int:user_id>/groups/', views.manage_user_groups, name='manage-user-groups'),

]