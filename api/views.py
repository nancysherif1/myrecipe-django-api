from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from .models import Order, Menu, Item, Contain, Vendor
from django.db.models import Sum, F, Count

from .serializers import (
    UserSerializer, 
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, 
    UserDetailSerializer,
    CustomerRegistrationSerializer,
    VendorRegistrationSerializer,
    CustomerSerializer,
    VendorSerializer,
)
from .models import Customer, Vendor

class UserDetailView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uid = serializer.validated_data['uid']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            try:
                uid = force_str(urlsafe_base64_decode(uid))
                user = get_user_model().objects.get(pk=uid)
                if default_token_generator.check_token(user, token):
                    user.set_password(new_password)
                    user.save()
                    return Response({'message': 'Password has been reset.'}, status=status.HTTP_200_OK)
                return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
            except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
                return Response({'error': 'Invalid user.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            User = get_user_model()
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = f"http://example.com/reset-password/{uid}/{token}/"
                send_mail(
                    'Password Reset Request',
                    f'Click the link to reset your password: {reset_link}',
                    'from@example.com',
                    [email],
                    fail_silently=False,
                )
                return Response({'message': 'Password reset email sent.'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                # Return the same message to avoid revealing user existence
                return Response({'message': 'Password reset email sent.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]

class RegisterView(CreateAPIView):
    """General user registration without specific type assignment"""
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class CustomerRegistrationView(CreateAPIView):
    """Register a new customer with user account"""
    serializer_class = CustomerRegistrationSerializer
    permission_classes = [AllowAny]

class VendorRegistrationView(CreateAPIView):
    """Register a new vendor with user account"""
    serializer_class = VendorRegistrationSerializer
    permission_classes = [AllowAny]

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Return user profile based on user type
        """
        user = request.user
        
        # Base user data
        data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
        
        # Check user type and add specific profile data
        if hasattr(user, 'customer'):
            data['user_type'] = 'customer'
            customer_data = CustomerSerializer(user.customer).data
            data.update(customer_data)
        elif hasattr(user, 'vendor'):
            data['user_type'] = 'vendor'
            vendor_data = VendorSerializer(user.vendor).data
            data.update(vendor_data)
        else:
            data['user_type'] = None
        
        return Response(data)

class VendorOrdersView(APIView):
    """
    Endpoint to get orders for a vendor
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a vendor
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can access this endpoint"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        # Get all orders that contain items from this vendor
        orders_data = []
        
        # Find all items that belong to this vendor
        vendor_items = Item.objects.filter(vendor=vendor).values_list('id', flat=True)
        
        # Find all order-item relationships that contain these items
        order_items = Contain.objects.filter(item_id__in=vendor_items)
        
        # Group by order to avoid duplicates
        processed_orders = set()
        
        for order_item in order_items:
            order = order_item.order
            
            # Skip if we've already processed this order
            if order.id in processed_orders:
                continue
                
            processed_orders.add(order.id)
            
            # Get all items in this order that belong to this vendor
            order_contains = Contain.objects.filter(
                order=order,
                item__vendor=vendor
            ).select_related('item')
            
            # Calculate total for this vendor's items in the order
            vendor_total = sum(oc.item.price * oc.quantity for oc in order_contains)
            
            # Get item details
            items_details = []
            for oc in order_contains:
                items_details.append({
                    "itemName": oc.item.name,
                    "quantity": oc.quantity,
                    "price": float(oc.item.price),
                    "subtotal": float(oc.item.price * oc.quantity)
                })
            
            # Build order data
            order_data = {
                "orderId": order.id,
                "orderDate": order.date,
                "customerName": order.customer.name,
                "customerEmail": order.customer.email,
                "customerPhone": order.customer.phone,
                "items": items_details,
                "totalOrderPrice": float(vendor_total),
                "status": order.status or "Pending"
            }
            
            orders_data.append(order_data)
        
        return Response(orders_data)

class CustomerMenusView(APIView):
    """
    Endpoint to get all menus with items for a customer
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a customer
        if not hasattr(request.user, 'customer'):
            return Response(
                {"error": "Only customers can access this endpoint"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all menus with their items
        all_vendors = Vendor.objects.all()
        result = []
        
        for vendor in all_vendors:
            vendor_data = {
                "vendorId": vendor.id,
                "vendorName": vendor.name,
                "location": vendor.location,
                "workingHours": vendor.working_hours,
                "menus": []
            }
            
            # Get all menus for this vendor
            menus = Menu.objects.filter(vendor=vendor)
            
            for menu in menus:
                menu_data = {
                    "menuId": menu.id,
                    "menuName": menu.name,
                    "date": menu.date,
                    "items": []
                }
                
                # Get all items for this menu
                items = Item.objects.filter(menu=menu)
                
                for item in items:
                    # Get categories for this item
                    categories = list(item.categories.values_list('name', flat=True))
                    
                    item_data = {
                        "itemId": item.id,
                        "itemName": item.name,
                        "price": float(item.price),
                        "description": item.description or "",
                        "categories": categories
                    }
                    
                    menu_data["items"].append(item_data)
                
                vendor_data["menus"].append(menu_data)
            
            result.append(vendor_data)
        
        return Response(result)