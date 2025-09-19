from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    GoogleLoginView,
    EmailVerificationView,
    UserProfileView,
    UserAccountDeleteView,
    UserProfileUpdateView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),
    path('verify-email/<uuid:token>/', EmailVerificationView.as_view(), name='verify_email'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile_update'),
    path('delete-account/', UserAccountDeleteView.as_view(), name='delete_account'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]