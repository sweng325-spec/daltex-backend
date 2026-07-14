# views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.decorators import api_view, permission_classes   
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_permissions(request):
    """
    API view to return the current user's details, groups, and permissions.
    """
    user = request.user
    
    # Get all permissions (inherited from groups + assigned directly)
    permissions_list = list(user.get_all_permissions())
    
    # Get all assigned groups
    groups_list = list(user.groups.values_list('name', flat=True))

    return Response({
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "groups": groups_list,
        "permissions": permissions_list
    }, status=status.HTTP_200_OK)