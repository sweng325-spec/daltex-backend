# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # 1. Generate the standard JWT access & refresh tokens
        data = super().validate(attrs)
        
        # 2. Get the authenticated user
        user = self.user
        
        # 3. Retrieve all their permissions (combining direct & group permissions)
        # Returns a list like: ["custody.add_employee", "hardware_specs.view_assetcategory"]
        # permissions_list = list(user.get_all_permissions())
        groups_list = list(user.groups.values_list('name', flat=True))
        # 4. Inject user data and permissions list into the login API response
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'groups': groups_list,
            # 'permissions': permissions_list  # 🌟 This is what your frontend needs!
        }
        
        return data