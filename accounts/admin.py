from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Doctor, Patient
from django.utils.translation import gettext_lazy as _


admin.site.site_header = 'Patient Monitoring Chatbot Admin'


class UserAdmin(UserAdmin):
    model = User
    list_display = ["username", "email", "phone", "address", "role"]
    list_filter = ["role", "is_staff", "is_superuser", "is_active", "groups"]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": (
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "role",
        )
        }),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "first_name",
                "last_name",
                "email",
                "phone",
                "address",
                "role", 
                "password1", 
                "password2"
            ),
        }),
    )

admin.site.register(User, UserAdmin)
admin.site.register(Doctor)
admin.site.register(Patient)
