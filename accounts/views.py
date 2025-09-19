from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from ads.models import Ad
import logging

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer, 
    GoogleLoginSerializer,
    UserSerializer,
    EmailVerificationSerializer
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
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Send verification email
        self.send_verification_email(user, request)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please check your email to verify your account.'
        }, status=status.HTTP_201_CREATED)
    
    def send_verification_email(self, user, request):
        """Send email verification link."""
        try:
            state_code = getattr(request, 'state_code', 'IL')
            
            # Get domain from state mapping (reverse lookup)
            domain_mapping = {v: k for k, v in settings.STATE_DOMAIN_MAPPING.items()}
            domain = domain_mapping.get(state_code, 'desiloginil.com')
            
            verification_url = f"http://{domain}/verify-email/{user.email_verification_token}"
            
            context = {
                'user': user,
                'verification_url': verification_url,
                'domain': domain,
            }
            
            subject = f'Verify your email address'
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
            
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")

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
        
        # Changed from access_token to id_token (correct terminology)
        id_token_value = serializer.validated_data['id_token']
        
        try:
            # Verify Google id_token (this was always verifying an ID token anyway)
            idinfo = id_token.verify_oauth2_token(
                id_token_value,  # This is actually an ID token, not access token
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            email = idinfo['email']
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

class EmailVerificationView(generics.UpdateAPIView):
    """Email verification endpoint."""
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]
    
    def update(self, request, *args, **kwargs):
        token = kwargs.get('token')
        
        try:
            user = User.objects.get(email_verification_token=token)
            
            if user.email_verified:
                return Response({
                    'message': 'Email already verified.'
                })
            
            user.email_verified = True
            user.save(update_fields=['email_verified'])
            
            logger.info(f"Email verified for user {user.email}")
            
            return Response({
                'message': 'Email verified successfully. You can now log in.'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token'},
                status=status.HTTP_400_BAD_REQUEST
            )

class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user



class UserAccountDeleteView(generics.DestroyAPIView):
    """Delete user account endpoint."""
    
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Optional: Add password confirmation
        password = request.data.get('password')
        if password and not user.check_password(password):
            return Response(
                {'error': 'Invalid password confirmation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Instead of hard delete, mark as inactive and clear personal data
        user.is_active = False
        user.email = f"deleted_user_{user.id}@deleted.com"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.phone = ""
        user.avatar = None
        user.save()
        
        # Also mark all user's ads as deleted
        Ad.objects.filter(user=user).update(status='deleted')
        
        return Response({
            'message': 'Account deleted successfully'
        }, status=status.HTTP_200_OK)

class UserProfileUpdateView(generics.UpdateAPIView):
    """Update user profile with file upload support."""
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'user': serializer.data,
            'message': 'Profile updated successfully'
        })