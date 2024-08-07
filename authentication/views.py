from .serializers import UserSerializer
from rest_framework import generics
from django.contrib.auth import get_user_model


User = get_user_model()

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()

# class ResetPasswordView(generics.UpdateAPIView):
#     serializer_class = UserSerializer
#     queryset = User.objects.all()
#     lookup_field = 'username'
#     lookup_url_kwarg = 'username'
#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         instance.set_password(request.data.get('password'))
#         instance.save()
#         return super().update(request, *args, **kwargs)
