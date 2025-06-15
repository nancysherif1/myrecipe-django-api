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
from .models import Order, Menu, Item, Contain, Vendor, Cart, CartItem , Category
from django.db.models import Sum, F, Count
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404

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
    # MenuSerializer,
    ItemSerializer,
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
            
            # Build order data with comment
            order_data = {
                "orderId": order.id,
                "orderDate": order.date,
                "customerName": order.customer.name,
                "customerEmail": order.customer.email,
                "customerPhone": order.customer.phone,
                "comment": order.comment or "",  # NEW: Include customer comment for vendor
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
        """Process checkout and create order with optional comment"""
        customer = getattr(request.user, 'customer', None)
        if not customer:
            return Response({'error': 'Only customers can checkout.'}, status=status.HTTP_403_FORBIDDEN)

        # Get payment method and comment from request (both optional)
        payment_method = request.data.get('payment_method', 'Cash')
        comment = request.data.get('comment', '').strip()  # NEW: Get comment from request
        
        try:
            cart = Cart.objects.get(customer=customer)
            cart_items = cart.items.all()
            
            # Check if cart is empty
            if not cart_items.exists():
                return Response({'error': 'Cart is empty. Cannot checkout.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate total amount
            total_amount = sum(item.item.price * item.quantity for item in cart_items)
            
            # Create the order with comment
            order = Order.objects.create(
                customer=customer,
                total_amount=total_amount,
                status='Pending',
                payment_method=payment_method,
                comment=comment if comment else None  # NEW: Add comment to order
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
                    'comment': order.comment,  # NEW: Include comment in response
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
            
            # Build order data with comment
            order_data = {
                "orderId": order.id,
                "orderDate": order.date,
                "totalAmount": float(order.total_amount),
                "status": order.status or "Pending",
                "paymentMethod": order.payment_method or "Cash",
                "comment": order.comment or "",  # NEW: Include comment in response
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
        
class VendorMenuView(APIView):
    """
    GET: Retrieve vendor's own menus with items
    POST: Create a new menu with items for the vendor
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all menus and items for the authenticated vendor"""
        # Check if user is a vendor
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can access their menus"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        # Get all menus for this vendor
        menus = Menu.objects.filter(vendor=vendor).order_by('-date')
        
        menus_data = []
        
        for menu in menus:
            # Get all items for this menu
            items = Item.objects.filter(menu=menu)
            
            items_data = []
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
                
                items_data.append(item_data)
            
            menu_data = {
                "menuId": menu.id,
                "menuName": menu.name,
                "date": menu.date,
                "itemCount": len(items_data),
                "items": items_data
            }
            
            menus_data.append(menu_data)
        
        response_data = {
            "vendorInfo": {
                "vendorId": vendor.id,
                "vendorName": vendor.name,
                "location": vendor.location,
                "workingHours": vendor.working_hours
            },
            "menus": menus_data,
            "totalMenus": len(menus_data)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new menu with items for the authenticated vendor"""
        # Check if user is a vendor
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can create menus"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        # Extract data from request
        menu_name = request.data.get('menu_name')
        items_data = request.data.get('items', [])
        
        # Validate required fields
        if not menu_name:
            return Response(
                {"error": "Menu name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not items_data or not isinstance(items_data, list):
            return Response(
                {"error": "Items list is required and must be a non-empty array"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate items data
        for i, item_data in enumerate(items_data):
            if not item_data.get('name'):
                return Response(
                    {"error": f"Item {i+1}: name is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not item_data.get('price'):
                return Response(
                    {"error": f"Item {i+1}: price is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                float(item_data.get('price'))
            except (TypeError, ValueError):
                return Response(
                    {"error": f"Item {i+1}: price must be a valid number"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            with transaction.atomic():
                # Create the menu
                menu = Menu.objects.create(
                    vendor=vendor,
                    name=menu_name
                )
                
                created_items = []
                
                # Create items for the menu
                for item_data in items_data:
                    item = Item.objects.create(
                        vendor=vendor,
                        menu=menu,
                        name=item_data['name'],
                        price=float(item_data['price']),
                        description=item_data.get('description', '')
                    )
                    
                    # Handle categories if provided
                    categories_data = item_data.get('categories', [])
                    created_categories = []
                    
                    for category_name in categories_data:
                        if category_name.strip():  # Only create non-empty categories
                            category = Category.objects.create(
                                item=item,
                                name=category_name.strip(),
                                description=f"Category for {item.name}"
                            )
                            created_categories.append(category_name.strip())
                    
                    item_response_data = {
                        "itemId": item.id,
                        "itemName": item.name,
                        "price": float(item.price),
                        "description": item.description,
                        "categories": created_categories
                    }
                    
                    created_items.append(item_response_data)
                
                # Prepare success response
                response_data = {
                    "message": "Menu created successfully",
                    "menu": {
                        "menuId": menu.id,
                        "menuName": menu.name,
                        "date": menu.date,
                        "vendorName": vendor.name,
                        "itemCount": len(created_items),
                        "items": created_items
                    }
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {"error": f"Failed to create menu: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VendorMenuDetailView(APIView):
    """
    GET: Retrieve a specific menu with its items
    PUT: Update menu name and/or add new items
    DELETE: Delete a menu
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, menu_id):
        """Get a specific menu with its items"""
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can access their menus"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        # Get the menu and ensure it belongs to the vendor
        menu = get_object_or_404(Menu, id=menu_id, vendor=vendor)
        
        # Get all items for this menu
        items = Item.objects.filter(menu=menu)
        
        items_data = []
        for item in items:
            categories = list(item.categories.values_list('name', flat=True))
            
            item_data = {
                "itemId": item.id,
                "itemName": item.name,
                "price": float(item.price),
                "description": item.description or "",
                "categories": categories
            }
            items_data.append(item_data)
        
        menu_data = {
            "menuId": menu.id,
            "menuName": menu.name,
            "date": menu.date,
            "itemCount": len(items_data),
            "items": items_data
        }
        
        return Response(menu_data, status=status.HTTP_200_OK)
    
    def put(self, request, menu_id):
        """Update menu name and/or add new items"""
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can update their menus"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        # Get the menu and ensure it belongs to the vendor
        menu = get_object_or_404(Menu, id=menu_id, vendor=vendor)
        
        # Extract data from request
        menu_name = request.data.get('menu_name')
        new_items_data = request.data.get('new_items', [])
        
        # Validate that at least one update is provided
        if not menu_name and not new_items_data:
            return Response(
                {"error": "Either menu_name or new_items must be provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Update menu name if provided - ONLY update the name field
                if menu_name and menu_name.strip():
                    new_name = menu_name.strip()
                    if new_name != menu.name:  # Only save if name actually changed
                        menu.name = new_name
                        menu.save(update_fields=['name'])  # FIXED: Only update name field, leave date untouched
                
                created_items = []
                
                # Add new items if provided
                if new_items_data and isinstance(new_items_data, list):
                    for item_data in new_items_data:
                        # Validate item data
                        if not item_data.get('name') or not item_data.get('name').strip():
                            return Response(
                                {"error": "Item name is required and cannot be empty"}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        if not item_data.get('price'):
                            return Response(
                                {"error": "Item price is required"}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        try:
                            price = float(item_data.get('price'))
                            if price < 0:
                                return Response(
                                    {"error": "Item price cannot be negative"}, 
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                        except (TypeError, ValueError):
                            return Response(
                                {"error": "Item price must be a valid number"}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        # Create the item
                        item = Item.objects.create(
                            vendor=vendor,
                            menu=menu,
                            name=item_data['name'].strip(),
                            price=price,
                            description=item_data.get('description', '').strip()
                        )
                        
                        # Handle categories if provided
                        categories_data = item_data.get('categories', [])
                        created_categories = []
                        
                        if categories_data:
                            for category_name in categories_data:
                                if category_name and category_name.strip():
                                    category = Category.objects.create(
                                        item=item,
                                        name=category_name.strip(),
                                        description=f"Category for {item.name}"
                                    )
                                    created_categories.append(category_name.strip())
                        
                        item_response_data = {
                            "itemId": item.id,
                            "itemName": item.name,
                            "price": float(item.price),
                            "description": item.description,
                            "categories": created_categories
                        }
                        
                        created_items.append(item_response_data)
                
                # Get updated menu data
                all_items = Item.objects.filter(menu=menu)
                all_items_data = []
                
                for item in all_items:
                    categories = list(item.categories.values_list('name', flat=True))
                    
                    item_data = {
                        "itemId": item.id,
                        "itemName": item.name,
                        "price": float(item.price),
                        "description": item.description or "",
                        "categories": categories
                    }
                    all_items_data.append(item_data)
                
                response_data = {
                    "message": "Menu updated successfully",
                    "menu": {
                        "menuId": menu.id,
                        "menuName": menu.name,
                        "date": menu.date,
                        "itemCount": len(all_items_data),
                        "items": all_items_data
                    },
                    "newItemsAdded": len(created_items)
                }
                
                return Response(response_data, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {"error": f"Failed to update menu: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, menu_id):
        """Delete a menu"""
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can delete their menus"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        # Get the menu and ensure it belongs to the vendor
        menu = get_object_or_404(Menu, id=menu_id, vendor=vendor)
        
        try:
            menu_name = menu.name
            menu.delete()
            
            return Response(
                {"message": f"Menu '{menu_name}' deleted successfully"}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Failed to delete menu: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class VendorMenuItemView(APIView):
    """
    DELETE: Delete a specific item from a menu
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, menu_id, item_id):
        """Delete a specific item from a menu"""
        # Check if user is a vendor
        if not hasattr(request.user, 'vendor'):
            return Response(
                {"error": "Only vendors can delete menu items"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor = request.user.vendor
        
        try:
            # Get the menu and ensure it belongs to the vendor
            menu = Menu.objects.get(id=menu_id, vendor=vendor)
        except Menu.DoesNotExist:
            return Response(
                {"error": "Menu not found or doesn't belong to you"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Get the item and ensure it belongs to the menu and vendor
            item = Item.objects.get(id=item_id, menu=menu, vendor=vendor)
        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found in this menu or doesn't belong to you"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Store item details before deletion
            item_name = item.name
            item_price = float(item.price)
            
            # Check if item is used in any existing orders
            order_contains = Contain.objects.filter(item=item)
            if order_contains.exists():
                return Response(
                    {
                        "error": f"Cannot delete '{item_name}' because it's part of existing orders",
                        "suggestion": "Items that are part of orders cannot be deleted to maintain order history integrity"
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Delete the item (categories will be deleted automatically due to CASCADE)
            item.delete()
            
            # Get updated menu statistics
            remaining_items = Item.objects.filter(menu=menu).count()
            
            response_data = {
                "message": f"Item '{item_name}' deleted successfully from menu '{menu.name}'",
                "deletedItem": {
                    "itemId": item_id,
                    "itemName": item_name,
                    "price": item_price
                },
                "menuInfo": {
                    "menuId": menu.id,
                    "menuName": menu.name,
                    "remainingItems": remaining_items
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to delete item: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )