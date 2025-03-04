from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    user = request.user
    if user.role == 'patient':
        return redirect('chat:home')
    elif user.role == 'doctor':
        return redirect('dashboard:home')
    return redirect('admin:index')

def hello(request):
    from django.http import JsonResponse
    return JsonResponse({'message': 'Hello, world!'})
