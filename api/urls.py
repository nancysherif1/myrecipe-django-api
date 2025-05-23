from django.urls import path
from .views import (
    RegisterView, 
    LoginView, 
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserDetailView,
    CustomerRegistrationView,
    VendorRegistrationView,
    UserProfileView,
    VendorOrdersView,
    CustomerMenusView,
    CartView,
)

urlpatterns = [
    # Auth routes
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # User info routes
    path('user/', UserDetailView.as_view(), name='user-detail'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    
    # User type specific registration
    path('register/customer/', CustomerRegistrationView.as_view(), name='register-customer'),
    path('register/vendor/', VendorRegistrationView.as_view(), name='register-vendor'),
    
    # Vendor and Customer specific routes
    path('vendor/orders/', VendorOrdersView.as_view(), name='vendor-orders'),
    path('customer/menus/', CustomerMenusView.as_view(), name='customer-menus'),
    #  made by me
    path('cart/', CartView.as_view(), name='cart'),
]