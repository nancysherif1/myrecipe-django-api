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
from .models import Order, Menu, Item, Contain, Vendor, Cart, CartItem
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
    CartSerializer,
    CartItemSerializer,
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

# Cart functionality - Fixed and completed
class CartView(APIView):
    """
    Handle cart operations: GET (display), POST (add items)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Display cart contents"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers have carts.'}, status=status.HTTP_403_FORBIDDEN)

        cart, created = Cart.objects.get_or_create(customer=customer)
        
        # Calculate cart total
        cart_items = cart.items.all()
        total = sum(item.item.price * item.quantity for item in cart_items)
        
        # Serialize cart data
        serializer = CartSerializer(cart)
        response_data = serializer.data
        response_data['total'] = float(total)
        response_data['item_count'] = cart_items.count()
        
        return Response(response_data)

    def post(self, request):
        """Add item to cart"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers can add to cart.'}, status=status.HTTP_403_FORBIDDEN)

        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity', 1)
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        if not item_id:
            return Response({'error': 'Item ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item = Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            return Response({'error': 'Item not found.'}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(customer=customer)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)

        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity

        cart_item.save()

        return Response({
            'message': f"{item.name} added to cart.",
            'item_name': item.name,
            'quantity_in_cart': cart_item.quantity
        }, status=status.HTTP_200_OK)


class CartItemView(APIView):
    """
    Handle individual cart item operations: PUT (update), DELETE (remove)
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        """Update quantity of item in cart"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers can modify cart.'}, status=status.HTTP_403_FORBIDDEN)

        quantity = request.data.get('quantity')
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cart = Cart.objects.get(customer=customer)
            cart_item = CartItem.objects.get(cart=cart, item_id=item_id)
            
            cart_item.quantity = quantity
            cart_item.save()
            
            return Response({
                'message': f"Updated {cart_item.item.name} quantity to {quantity}.",
                'item_name': cart_item.item.name,
                'new_quantity': quantity
            }, status=status.HTTP_200_OK)
            
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, item_id):
        """Remove item from cart"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers can modify cart.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            cart = Cart.objects.get(customer=customer)
            cart_item = CartItem.objects.get(cart=cart, item_id=item_id)
            
            item_name = cart_item.item.name
            cart_item.delete()
            
            return Response({
                'message': f"{item_name} removed from cart."
            }, status=status.HTTP_200_OK)
            
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)


class CartClearView(APIView):
    """
    Clear all items from cart
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """Clear entire cart"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers can clear cart.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            cart = Cart.objects.get(customer=customer)
            items_count = cart.items.count()
            cart.items.all().delete()
            
            return Response({
                'message': f"Cart cleared. {items_count} items removed."
            }, status=status.HTTP_200_OK)
            
        except Cart.DoesNotExist:
            return Response({
                'message': 'Cart is already empty.'
            }, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    """
    Handle cart checkout - convert cart items to order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Process checkout and create order"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers can checkout.'}, status=status.HTTP_403_FORBIDDEN)

        # Get payment method from request (optional)
        payment_method = request.data.get('payment_method', 'Cash')
        
        try:
            cart = Cart.objects.get(customer=customer)
            cart_items = cart.items.all()
            
            # Check if cart is empty
            if not cart_items.exists():
                return Response({'error': 'Cart is empty. Cannot checkout.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate total amount
            total_amount = sum(item.item.price * item.quantity for item in cart_items)
            
            # Create the order
            order = Order.objects.create(
                customer=customer,
                total_amount=total_amount,
                status='Pending',
                payment_method=payment_method
            )
            
            # Create order items (Contain relationships)
            order_items_created = []
            for cart_item in cart_items:
                contain = Contain.objects.create(
                    order=order,
                    item=cart_item.item,
                    quantity=cart_item.quantity
                )
                order_items_created.append({
                    'item_name': cart_item.item.name,
                    'quantity': cart_item.quantity,
                    'price': float(cart_item.item.price),
                    'subtotal': float(cart_item.item.price * cart_item.quantity),
                    'vendor': cart_item.item.vendor.name
                })
            
            # Clear the cart after successful checkout
            cart.items.all().delete()
            
            # Prepare response data
            response_data = {
                'message': 'Checkout successful!',
                'order': {
                    'order_id': order.id,
                    'customer_name': customer.name,
                    'order_date': order.date,
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'payment_method': order.payment_method,
                    'items': order_items_created,
                    'item_count': len(order_items_created)
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found or is empty.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Checkout failed. Please try again.',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CustomerOrdersView(APIView):
    """
    Endpoint to get orders for a customer
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check if user is a customer
        if not hasattr(request.user, 'customer'):
            return Response(
                {"error": "Only customers can access this endpoint"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = request.user.customer
        
        # Get all orders for this customer
        orders = Order.objects.filter(customer=customer).order_by('-date')
        
        orders_data = []
        
        for order in orders:
            # Get all items in this order with their details
            order_contains = Contain.objects.filter(order=order).select_related('item', 'item__vendor')
            
            # Get item details
            items_details = []
            for oc in order_contains:
                items_details.append({
                    "itemId": oc.item.id,
                    "itemName": oc.item.name,
                    "quantity": oc.quantity,
                    "price": float(oc.item.price),
                    "subtotal": float(oc.item.price * oc.quantity),
                    "vendorName": oc.item.vendor.name,
                    "vendorId": oc.item.vendor.id,
                    "description": oc.item.description or ""
                })
            
            # Group items by vendor for better organization
            vendors_data = {}
            for item in items_details:
                vendor_id = item['vendorId']
                vendor_name = item['vendorName']
                
                if vendor_id not in vendors_data:
                    vendors_data[vendor_id] = {
                        "vendorId": vendor_id,
                        "vendorName": vendor_name,
                        "items": [],
                        "vendorTotal": 0
                    }
                
                vendors_data[vendor_id]["items"].append({
                    "itemId": item["itemId"],
                    "itemName": item["itemName"],
                    "quantity": item["quantity"],
                    "price": item["price"],
                    "subtotal": item["subtotal"],
                    "description": item["description"]
                })
                vendors_data[vendor_id]["vendorTotal"] += item["subtotal"]
            
            # Convert vendors_data dict to list
            vendors_list = list(vendors_data.values())
            
            # Build order data
            order_data = {
                "orderId": order.id,
                "orderDate": order.date,
                "totalAmount": float(order.total_amount),
                "status": order.status or "Pending",
                "paymentMethod": order.payment_method or "Cash",
                "itemCount": sum(item["quantity"] for item in items_details),
                "vendorCount": len(vendors_data),
                "items": items_details,  # All items in a flat list
                "vendors": vendors_list  # Items grouped by vendor
            }
            
            orders_data.append(order_data)
        
        # Add summary data
        response_data = {
            "orders": orders_data,
            "totalOrders": len(orders_data),
            "customerInfo": {
                "customerId": customer.id,
                "customerName": customer.name,
                "customerEmail": customer.email
            }
        }
        
        return Response(response_data)