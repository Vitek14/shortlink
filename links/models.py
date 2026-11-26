from django.db import models
from django.utils import timezone
import string
import random
from django.contrib.auth import get_user_model

User = get_user_model()


class Link(models.Model):
    original_url = models.URLField(max_length=2000)
    short_code = models.CharField(max_length=20, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    click_count = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='links')

    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def increment_clicks(self):
        from django.db.models import F
        self.click_count = F('click_count') + 1
        self.save(update_fields=['click_count'])

    @staticmethod
    def generate_unique_code(length=6):
        chars = string.ascii_letters + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Link.objects.filter(short_code=code).exists():
                return code

    def __str__(self):
        return f"{self.short_code} -> {self.original_url[:50]}"


class ClickLog(models.Model):
    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name='clicks')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        return f"Click on {self.link.short_code} at {self.timestamp}"
