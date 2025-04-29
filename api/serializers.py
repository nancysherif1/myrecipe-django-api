from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Vendor, Employee

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