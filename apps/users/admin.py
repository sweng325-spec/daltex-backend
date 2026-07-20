# custody/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile  # Now importing from custody/models.py

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Information'

class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = BaseUserAdmin.list_display + ('get_role',)

    def get_role(self, instance):
        return instance.profile.role if hasattr(instance, 'profile') else "No Role Assigned"

    get_role.short_description = 'Role'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)