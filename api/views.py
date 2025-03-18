from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from .serializers import UserSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from .serializers import PasswordResetRequestSerializer
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .serializers import PasswordResetConfirmSerializer
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .serializers import UserDetailSerializer


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
                reset_link = f"http://example.com/reset-password/{uid}/{token}/"  # Replace with your frontend URL
                send_mail(
                    'Password Reset Request',
                    f'Click the link to reset your password: {reset_link}',
                    'from@example.com',  # Replace with your email
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
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

