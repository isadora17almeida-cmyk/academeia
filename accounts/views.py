from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required

from .forms import NeonAuthenticationForm, ProfileForm, RegisterForm


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = NeonAuthenticationForm
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    pass


def register(request):
    if request.user.is_authenticated:
        return redirect('studies:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Conta criada com sucesso. Bem-vindo ao ACADEME.IA!')
            return redirect('studies:dashboard')
        messages.error(request, 'Revise os campos destacados para criar sua conta.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    profile_obj = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile_obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('accounts:profile')
        messages.error(request, 'Não foi possível atualizar seu perfil.')
    else:
        form = ProfileForm(instance=profile_obj, user=request.user)
    return render(request, 'accounts/profile.html', {'form': form})
