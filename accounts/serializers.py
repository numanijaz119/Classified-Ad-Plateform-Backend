from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
import uuid

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'phone',
            'password', 'password_confirm'
        )
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields didn't match."}
            )
        
        # Validate password strength
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # TODO: Send email verification in Phase 1
        # send_verification_email.delay(user.id)
        
        return user

class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,  # Our custom user model uses email as username
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    'Unable to log in with provided credentials.',
                    code='authorization'
                )
            
            if not user.email_verified:
                raise serializers.ValidationError(
                    'Please verify your email address before logging in.',
                    code='email_not_verified'
                )
            
            if user.is_suspended:
                raise serializers.ValidationError(
                    'Your account has been suspended. Please contact support.',
                    code='account_suspended'
                )
        else:
            raise serializers.ValidationError(
                'Must include email and password.',
                code='required'
            )
        
        data['user'] = user
        return data

class GoogleLoginSerializer(serializers.Serializer):
    """Serializer for Google OAuth login."""
    id_token = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for responses."""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'avatar', 'email_verified', 'created_at'
        )
        read_only_fields = ('id', 'email_verified', 'created_at')

class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    token = serializers.UUIDField()