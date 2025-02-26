from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Doctor, Patient

admin.site.site_header = 'Patient Monitoring Chatbot Admin'
admin.site.site_title = 'Admin Portal'
admin.site.index_title = 'Welcome to the Admin Portal'


@admin.register(User)
class UserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'phone', 'address', 'role']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_active', 'groups']
    search_fields = ['username', 'email', 'phone', 'address']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'role'),
            'classes': ('wide',),
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'phone', 'department']
    search_fields = ['user__username', 'user__email', 'department']
    list_filter = ['department']
    ordering = ['user__username']

    def email(self, obj):
        return obj.user.email

    def phone(self, obj):
        return obj.user.phone


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'phone']
    search_fields = ['user__username', 'user__email']
    ordering = ['user__username']

    def email(self, obj):
        return obj.user.email

    def phone(self, obj):
        return obj.user.phone
