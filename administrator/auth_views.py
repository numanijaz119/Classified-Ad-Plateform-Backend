# administrator/auth_views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
import logging

from accounts.models import User
from accounts.serializers import UserSerializer
from core.utils import get_client_ip

logger = logging.getLogger(__name__)


class AdminLoginView(generics.GenericAPIView):
    """
    Admin/Staff login endpoint.
    Only allows users with is_staff=True or is_superuser=True.
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').lower().strip()
        password = request.data.get('password', '')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = authenticate(request, email=email, password=password)
        
        if user is None:
            logger.warning(f"Failed admin login attempt for {email}")
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user is staff or superuser
        if not (user.is_staff or user.is_superuser):
            logger.warning(f"Non-staff user {email} attempted admin login")
            return Response(
                {'error': 'Access denied. Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if account is active
        if not user.is_active:
            return Response(
                {'error': 'This account has been deactivated.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if account is suspended
        if user.is_suspended:
            return Response(
                {'error': 'This account has been suspended. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Email verification not required for admin login
        # (admins are verified by superadmin when created)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims to token
        refresh['is_admin'] = True
        refresh['is_staff'] = user.is_staff
        refresh['is_superuser'] = user.is_superuser
        
        # Update last login
        user.last_login = timezone.now()
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['last_login', 'last_login_ip'])
        
        logger.info(f"Admin login successful: {user.email} (staff={user.is_staff}, super={user.is_superuser})")
        
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'avatar': request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Admin login successful.'
        }, status=status.HTTP_200_OK)


class AdminLogoutView(generics.GenericAPIView):
    """Admin logout endpoint."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logger.info(f"Admin logout: {request.user.email}")
            
            return Response({
                'message': 'Logged out successfully.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Admin logout error: {str(e)}")
            return Response({
                'error': 'Logout failed.'
            }, status=status.HTTP_400_BAD_REQUEST)


class AdminProfileView(generics.GenericAPIView):
    """Get admin profile information."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Verify user is staff
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = request.user
        
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'phone': user.phone,
            'avatar': request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'email_verified': user.email_verified,
            'created_at': user.created_at,
            'last_login': user.last_login,
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_verify_token(request):
    """
    Verify if a token is valid and belongs to an admin user.
    Used by frontend to check if user is still authenticated.
    """
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
    
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'error': 'Token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Verify token
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        
        # Get user
        user = User.objects.get(id=user_id)
        
        # Check if user is admin
        if not (user.is_staff or user.is_superuser):
            return Response(
                {'valid': False, 'error': 'Not an admin user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user is active
        if not user.is_active:
            return Response(
                {'valid': False, 'error': 'User is inactive.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({
            'valid': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.get_full_name(),
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        })
        
    except (TokenError, InvalidToken) as e:
        return Response(
            {'valid': False, 'error': 'Invalid or expired token.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except User.DoesNotExist:
        return Response(
            {'valid': False, 'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_change_password(request):
    """Change password for admin users."""
    
    # Verify user is admin
    if not (request.user.is_staff or request.user.is_superuser):
        return Response(
            {'error': 'Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response(
            {'error': 'Both old and new passwords are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify old password
    if not request.user.check_password(old_password):
        return Response(
            {'error': 'Current password is incorrect.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate new password
    if len(new_password) < 8:
        return Response(
            {'error': 'New password must be at least 8 characters long.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set new password
    request.user.set_password(new_password)
    request.user.save()
    
    logger.info(f"Admin password changed: {request.user.email}")
    
    return Response({
        'message': 'Password changed successfully.'
    })