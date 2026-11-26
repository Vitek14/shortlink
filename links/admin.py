from django.contrib import admin
from .models import Link, ClickLog


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('short_code', 'original_url', 'created_at', 'expires_at', 'is_active', 'click_count')
    search_fields = ('short_code', 'original_url')
    list_filter = ('is_active', 'created_at')


@admin.register(ClickLog)
class ClickLogAdmin(admin.ModelAdmin):
    list_display = ('link', 'timestamp', 'ip_address')
    list_filter = ('timestamp',)
