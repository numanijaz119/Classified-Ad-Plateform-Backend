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
        self.send_verification_email(user, request, verification_code)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please check your email for verification code.'
        }, status=status.HTTP_201_CREATED)
    
    def send_verification_email(self, user, request, verification_code):
        """Send email verification code."""
        try:
            state_code = getattr(request, 'state_code', 'IL')
            
            # Get domain from state mapping
            domain_mapping = {v: k for k, v in settings.STATE_DOMAIN_MAPPING.items()}
            domain = domain_mapping.get(state_code, 'desiloginil.com')
            
            context = {
                'user': user,
                'verification_code': verification_code,
                'domain': domain,
                'expires_in': 15,  # 15 minutes
            }
            
            subject = f'Your verification code for {domain}'
            message = render_to_string('emails/verification.txt', context)
            html_message = render_to_string('emails/verification.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Verification code sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")

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
            RegisterView().send_verification_email(user, request, verification_code)
            
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
    """Update user profile endpoint."""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

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
            self.send_password_reset_email(user, request, reset_code)
            
            return Response({
                'message': 'Password reset code sent to your email.'
            })
            
        except User.DoesNotExist:
            # Return success message even if user doesn't exist (security)
            return Response({
                'message': 'Password reset code sent to your email.'
            })
    
    def send_password_reset_email(self, user, request, reset_code):
        """Send password reset code via email."""
        try:
            state_code = getattr(request, 'state_code', 'IL')
            
            # Get domain from state mapping
            domain_mapping = {v: k for k, v in settings.STATE_DOMAIN_MAPPING.items()}
            domain = domain_mapping.get(state_code, 'desiloginil.com')
            
            context = {
                'user': user,
                'reset_code': reset_code,
                'domain': domain,
                'expires_in': 15,  # 15 minutes
            }
            
            subject = f'Password Reset Code for {domain}'
            message = render_to_string('emails/password_reset.txt', context)
            html_message = render_to_string('emails/password_reset.html', context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Password reset code sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")

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