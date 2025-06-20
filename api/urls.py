from django.urls import path
from .views import (
    CustomerOrdersView,
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
    CartItemView,
    CartClearView,
    CheckoutView,
    VendorMenuView,
    VendorMenuDetailView,
    VendorMenuItemView
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
    
    # Cart routes
    path('cart/', CartView.as_view(), name='cart'),  # GET: display cart, POST: add item
    path('cart/item/<int:item_id>/', CartItemView.as_view(), name='cart-item'),  # PUT: update quantity, DELETE: remove item
    path('cart/clear/', CartClearView.as_view(), name='cart-clear'),  # DELETE: clear entire cart
    path('cart/checkout/', CheckoutView.as_view(), name='checkout'),  # POST: process checkout

    path('customer/orders/', CustomerOrdersView.as_view(), name='customer-orders'),

     path('vendor/menus/', VendorMenuView.as_view(), name='vendor-menus'),  # GET: get all menus, POST: create menu
    path('vendor/menus/<int:menu_id>/', VendorMenuDetailView.as_view(), name='vendor-menu-detail'),  # GET, PUT, DELETE specific menu

    path('vendor/menus/<int:menu_id>/items/<int:item_id>/', VendorMenuItemView.as_view(), name='vendor-menu-item'),

]