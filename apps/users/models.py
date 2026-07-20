from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # 📝 Plain text field: allows any text up to 100 characters
    role = models.CharField(max_length=100, default='Viewer', blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"