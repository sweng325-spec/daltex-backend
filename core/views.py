# views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer,ChangePasswordSerializer
from rest_framework.decorators import api_view, permission_classes   
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import Group
from .serializers import GroupSerializer
from django.shortcuts import get_object_or_404

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
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 🛡️ Only authenticated users can change their password
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        
        # 1. Verify the old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": ["Wrong password. Please enter your correct current password."]}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 2. Set the new password (set_password automatically hashes it safely)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response(
            {"message": "Password updated successfully."}, 
            status=status.HTTP_200_OK
        )
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny  # Or use IsAdminUser for restricted access
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer

@api_view(['POST'])
@permission_classes([AllowAny]) # Change to [IsAdminUser] if only admins should call this
def create_user_with_group(request):
    """
    API View to register a new user account and directly associate them with
    pre-existing Django Permission Groups.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Format the response nicely, showing the assigned group names instead of just IDs
        return Response({
            "message": "User registered successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "groups": [group.name for group in user.groups.all()]
            }
        }, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # 🛡️ Only logged-in users can list groups
def list_groups(request):
    """
    API view to return all system permission groups (id and name).
    """
    groups = Group.objects.all().order_by('name')
    serializer = GroupSerializer(groups, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser  # 🛡️ Highly recommended for user directories
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .serializers import UserWithGroupsSerializer

@api_view(['GET'])
@permission_classes([IsAdminUser])  # Only admins can retrieve the user roster
def list_users_with_groups(request):
    """
    API view to return all users with their assigned permission groups.
    Optimized to prevent N+1 query execution.
    """
    # Use prefetch_related to load groups in one query instead of querying for each user
    users = User.objects.all().prefetch_related('groups').order_by('id')
    
    serializer = UserWithGroupsSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



from .serializers import UserGroupActionSerializer

@api_view(['PATCH'])
@permission_classes([IsAdminUser])  # 🛡️ Only admins should manage user permissions
def manage_user_groups(request, user_id):
    """
    API view to add, remove, or completely reset groups for a specific user.
    URL parameter: user_id (the ID of the target User)
    """
    # 1. Ensure the target user exists
    user = get_object_or_404(User, id=user_id)
    
    # 2. Validate incoming request payload
    serializer = UserGroupActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    action = serializer.validated_data['action']
    groups = serializer.validated_data['group_ids'] # This is a list of Group instances
    
    # 3. Perform the database operations based on chosen action
    if action == 'add':
        user.groups.add(*groups)
        message = f"Successfully added {len(groups)} group(s) to user {user.username}."
        
    elif action == 'remove':
        user.groups.remove(*groups)
        message = f"Successfully removed {len(groups)} group(s) from user {user.username}."
        
    elif action == 'set':
        user.groups.set(groups)
        message = f"Successfully updated user {user.username}'s groups to match the list."

    # 4. Return the updated state
    return Response({
        "message": message,
        "user": {
            "id": user.id,
            "username": user.username,
            "current_groups": [
                {"id": group.id, "name": group.name} for group in user.groups.all()
            ]
        }
    }, status=status.HTTP_200_OK)