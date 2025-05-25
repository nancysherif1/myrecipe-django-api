from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Vendor
from .models import Cart, CartItem, Item

class UserDetailSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'user_type']
    
    def get_user_type(self, obj):
        if hasattr(obj, 'customer'):
            return 'customer'
        elif hasattr(obj, 'vendor'):
            return 'vendor'
        return None

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'email', 'address', 'department_number', 
                 'building_number', 'street_number', 'city']
        read_only_fields = ['id']

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'location', 'working_hours']
        read_only_fields = ['id']


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Customer
        fields = ['user', 'name', 'phone', 'email', 'address', 'department_number', 
                 'building_number', 'street_number', 'city']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer().create(user_data)
        
        # Create customer and link to user
        customer = Customer.objects.create(
            user=user,
            name=validated_data.get('name', user.username),
            email=validated_data.get('email', user.email),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            department_number=validated_data.get('department_number', ''),
            building_number=validated_data.get('building_number', ''),
            street_number=validated_data.get('street_number', ''),
            city=validated_data.get('city', '')
        )
        
        return customer

class VendorRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Vendor
        fields = ['user', 'name', 'location', 'working_hours']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer().create(user_data)
        
        # Create vendor and link to user
        vendor = Vendor.objects.create(
            user=user,
            name=validated_data.get('name', user.username),
            location=validated_data.get('location', ''),
            working_hours=validated_data.get('working_hours', '')
        )
        
        return vendor

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()

# Cart Serializers - Enhanced
class CartItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_price = serializers.DecimalField(source='item.price', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='item.vendor.name', read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'item', 'item_name', 'item_price', 'quantity', 'subtotal', 'vendor_name']
        read_only_fields = ['id', 'item_name', 'item_price', 'subtotal', 'vendor_name']
    
    def get_subtotal(self, obj):
        return float(obj.item.price * obj.quantity)

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'customer', 'items', 'total_items', 'total_price']
        read_only_fields = ['id', 'customer', 'total_items', 'total_price']
    
    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())
    
    def get_total_price(self, obj):
        return float(sum(item.item.price * item.quantity for item in obj.items.all()))

# Additional serializer for item details when adding to cart
class ItemSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = Item
        fields = ['id', 'name', 'price', 'description', 'vendor_name']
        read_only_fields = ['id', 'name', 'price', 'description', 'vendor_name']