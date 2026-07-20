from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # 🌟 Update this to point to the correct nested path:
    name = 'apps.users'