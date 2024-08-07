from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Doctor, Patient
from django.utils.translation import gettext_lazy as _


admin.site.site_header = 'Patient Monitoring Chatbot Admin'

class UserAdmin(UserAdmin):
    model = User
    list_display = ["username", "phone", "address", "is_doctor", "is_patient"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": (
            "first_name", 
            "last_name", 
            "email",
            "phone", 
            "address", 
            "is_doctor", 
            "is_patient"
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

admin.site.register(User, UserAdmin)
admin.site.register(Doctor)
admin.site.register(Patient)
