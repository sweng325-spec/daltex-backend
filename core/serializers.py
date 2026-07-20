from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

class UserRegistrationSerializer(serializers.ModelSerializer):
    # Enforces Django's standard strong password rules
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    # Accept either a list of group IDs or group Names. 
    # Here we will accept Group IDs (Primary Keys) for clean API design.
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        help_text="List of Group IDs to assign this user to."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'groups']

    def create(self, validated_data):
        # 1. Extract groups from validated data so we can handle user creation first
        groups = validated_data.pop('groups', [])

        # 2. Create and hash the user's password securely using create_user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )

        # 3. Associate the user to the validated groups
        if groups:
            user.groups.set(groups)
            
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, 
        write_only=True, 
        validators=[validate_password]  # 🔒 Enforces Django's password strength rules
    )
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# 🌟 Update this import to point to your new nested app structure
from apps.users.models import UserProfile 

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # 1. Generate the standard JWT access & refresh tokens
        data = super().validate(attrs)
        
        # 2. Get the authenticated user
        user = self.user
        
        # 3. Retrieve their groups and permissions
        groups_list = list(user.groups.values_list('name', flat=True))
        # permissions_list = list(user.get_all_permissions())
        
        # 4. Safe retrieval of your custom plain-text role
        # We look up the related profile from the apps.users model.
        # Fallback to "Viewer" if the user profile doesn't exist yet.
        user_role = "Viewer"
        if hasattr(user, 'profile'):
            user_role = user.profile.role
        
        # 5. Inject user data, groups, role, and permissions into the login response
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'role': user_role,  # 🌟 Your plain-text role from apps.users.models.UserProfile
            'groups': groups_list,
            # 'permissions': permissions_list  # Helps your frontend manage routes
        }
        
        return data   
    
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']
        
        
class UserWithGroupsSerializer(serializers.ModelSerializer):
    # This nests the groups array inside each user representation
    groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'first_name', 
            'last_name', 
            'is_active', 
            'is_staff', 
            'groups'
        ]
        
class UserGroupActionSerializer(serializers.Serializer):
    ACTION_CHOICES = ['add', 'remove', 'set']
    
    action = serializers.ChoiceField(
        choices=ACTION_CHOICES, 
        required=True,
        help_text="'add' appends groups, 'remove' detaches them, 'set' overwrites the whole list."
    )
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=True,
        help_text="A list of Group IDs to process."
    )