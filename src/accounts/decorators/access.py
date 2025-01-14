from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def allow_only(allowed_roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_anonymous:
                return redirect('accounts:login')
            if request.user.role not in allowed_roles:
                raise PermissionDenied()
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
