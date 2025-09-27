from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    GoogleLoginView,
    EmailVerificationView,
    ResendVerificationView,
    UserProfileView,
    UserProfileUpdateView,
    UserPrivacySettingsView,
    delete_avatar,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    UserAccountDeleteView,
)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),
    
    # Email verification
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'), 
    path('verify-email/resend/', ResendVerificationView.as_view(), name='resend_verification'),
    
    # Password management
    path('password/forgot/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password/reset/', ResetPasswordView.as_view(), name='reset_password'),
    path('password/change/', ChangePasswordView.as_view(), name='change_password'),
    
    # Profile management
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile_update'),
    path('delete-account/', UserAccountDeleteView.as_view(), name='delete_account'),
    path('profile/privacy/', UserPrivacySettingsView.as_view(), name='privacy_settings'),
    path('profile/avatar/delete/', delete_avatar, name='delete_avatar'),
    
    # Token management
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]