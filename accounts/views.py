from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import logging
import random
import string
from rest_framework.parsers import MultiPartParser, FormParser
from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer, 
    GoogleLoginSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    EmailVerificationSerializer,
    ResendVerificationSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer
)
from core.utils import get_client_ip
from core.email_utils import send_verification_email, send_password_reset_email

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Generate 6-digit verification code with expiry
        verification_code = ''.join(random.choices(string.digits, k=6))
        user.set_email_verification_code(verification_code)
        user.save(update_fields=['email_verification_token', 'email_verification_expires'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Send verification email
        try:
            send_verification_email(user, request, verification_code)
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            # Don't fail registration if email fails
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please check your email for verification code.'
        }, status=status.HTTP_201_CREATED)
    

class EmailVerificationView(generics.CreateAPIView):
    """Email verification endpoint using code."""
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        
        try:
            user = User.objects.get(
                email_verification_token=code,
                email_verification_expires__gt=timezone.now()
            )
            
            if user.email_verified:
                return Response({
                    'message': 'Email already verified.'
                })
            
            user.email_verified = True
            user.clear_email_verification()
            user.save(update_fields=['email_verified', 'email_verification_token', 'email_verification_expires'])
            
            logger.info(f"Email verified for user {user.email}")
            
            return Response({
                'message': 'Email verified successfully. You can now log in.'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )

class ResendVerificationView(generics.CreateAPIView):
    """Resend email verification code."""
    permission_classes = [AllowAny]
    serializer_class = ResendVerificationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, email_verified=False)
            
            # Generate new 6-digit verification code
            verification_code = ''.join(random.choices(string.digits, k=6))
            user.set_email_verification_code(verification_code)
            user.save(update_fields=['email_verification_token', 'email_verification_expires'])
            
            # Send verification email
            try:
                send_verification_email(user, request, verification_code)
                logger.info(f"Resend verification email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to resend verification email to {user.email}: {str(e)}")
                return Response(
                    {'error': 'Failed to send verification email. Please try again later.'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                'message': 'New verification code sent successfully.'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found or already verified'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class LoginView(generics.CreateAPIView):
    """User login endpoint."""
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Update last login IP
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['last_login_ip'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Login successful.'
        })

class GoogleLoginView(generics.CreateAPIView):
    """Google OAuth login endpoint."""
    serializer_class = GoogleLoginSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        id_token_value = serializer.validated_data['id_token']
        
        try:
            # Verify Google ID token
            idinfo = id_token.verify_oauth2_token(
                id_token_value,
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            email = idinfo['email'].lower()
            google_id = idinfo['sub']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'google_id': google_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email_verified': True,  # Google accounts are pre-verified
                }
            )
            
            # Update Google ID if user exists but doesn't have it
            if not created and not user.google_id:
                user.google_id = google_id
                user.email_verified = True
                user.save(update_fields=['google_id', 'email_verified'])
            
            # Check account status
            if not user.is_active:
                return Response(
                    {'error': 'Account is disabled'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if user.is_suspended:
                return Response(
                    {'error': 'Account has been suspended'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update last login IP
            user.last_login_ip = get_client_ip(request)
            user.save(update_fields=['last_login_ip'])
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            message = 'Account created successfully.' if created else 'Login successful.'
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'message': message
            })
            
        except ValueError as e:
            logger.error(f"Google token verification failed: {str(e)}")
            return Response(
                {'error': 'Invalid Google token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class UserProfileView(generics.RetrieveAPIView):
    """Get user profile endpoint."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserProfileUpdateView(generics.UpdateAPIView):
    """Update user profile endpoint with avatar upload support."""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle avatar upload
        avatar = request.FILES.get('avatar')
        if avatar:
            # Delete old avatar if exists
            if instance.avatar:
                instance.avatar.delete(save=False)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'user': UserSerializer(instance).data,
            'message': 'Profile updated successfully.'
        })

class UserPrivacySettingsView(generics.UpdateAPIView):
    """Update privacy settings endpoint."""
    serializer_class = UserPrivacySettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'settings': serializer.data,
            'message': 'Privacy settings updated successfully.'
        })

@api_view(['DELETE'])
def delete_avatar(request):
    """Delete user avatar."""
    user = request.user
    
    if user.avatar:
        user.avatar.delete(save=False)
        user.avatar = None
        user.save(update_fields=['avatar'])
        return Response({'message': 'Avatar deleted successfully.'})
    
    return Response(
        {'error': 'No avatar to delete.'},
        status=status.HTTP_404_NOT_FOUND
    )


class ForgotPasswordView(generics.CreateAPIView):
    """Forgot password endpoint - sends reset code via email."""
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            if user.is_suspended:
                return Response(
                    {'error': 'Account has been suspended'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate 6-digit reset code
            reset_code = ''.join(random.choices(string.digits, k=6))
            user.set_password_reset_code(reset_code)
            user.save(update_fields=['password_reset_token', 'password_reset_expires'])
            
            # Send reset email
            try:
                send_password_reset_email(user, request, reset_code)
                logger.info(f"Password reset email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
                # Don't reveal if user exists or not for security
            
            return Response({
                'message': 'Password reset code sent to your email.'
            })
            
        except User.DoesNotExist:
            # Return success message even if user doesn't exist (security)
            return Response({
                'message': 'Password reset code sent to your email.'
            })
    

class ResetPasswordView(generics.CreateAPIView):
    """Reset password using code endpoint."""
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(
                email=email,
                password_reset_token=code,
                password_reset_expires__gt=timezone.now()
            )
            
            # Set new password
            user.set_password(new_password)
            user.clear_password_reset()
            user.save(update_fields=['password', 'password_reset_token', 'password_reset_expires'])
            
            logger.info(f"Password reset successful for user {user.email}")
            
            return Response({
                'message': 'Password reset successful. You can now log in with your new password.'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired reset code'},
                status=status.HTTP_400_BAD_REQUEST
            )

class ChangePasswordView(generics.CreateAPIView):
    """Change password for authenticated users."""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        new_password = serializer.validated_data['new_password']
        
        # Set new password
        user.set_password(new_password)
        user.save(update_fields=['password'])
        
        logger.info(f"Password changed for user {user.email}")
        
        return Response({
            'message': 'Password changed successfully.'
        })

class UserAccountDeleteView(generics.DestroyAPIView):
    """Delete user account endpoint."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def perform_destroy(self, instance):
        # Log account deletion
        logger.info(f"Account deleted for user {instance.email}")
        instance.delete()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'message': 'Account deleted successfully.'
        }, status=status.HTTP_200_OK)

class LogoutView(generics.CreateAPIView):
    """Logout endpoint to handle any server-side cleanup."""
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        try:
            # Get refresh token from request
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                # Blacklist the refresh token
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logger.info(f"User {request.user.email} logged out")
            
            return Response({
                'message': 'Logged out successfully.'
            })
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'message': 'Logged out successfully.'
            })  # Return success even if token blacklisting fails