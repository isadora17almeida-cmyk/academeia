from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'study_area', 'college', 'objective', 'created_at')
    search_fields = ('user__username', 'user__email', 'full_name', 'college')
    list_filter = ('study_area', 'created_at')
