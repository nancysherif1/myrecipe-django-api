# api/urls.py
from django.urls import path
from .views import RegisterView, LoginView, PasswordResetRequestView, PasswordResetConfirmView, UserDetailView

urlpatterns = [
    path('user-details/', UserDetailView.as_view(), name='user-details'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
