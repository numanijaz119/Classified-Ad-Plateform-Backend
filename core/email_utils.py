import logging
from typing import List, Dict, Any, Optional
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

class EmailService:
    """Centralized email service for sending emails using HTML templates."""
    
    @staticmethod
    def _get_domain_from_request(request) -> str:
        """Get domain based on state from request."""
        state_code = getattr(request, 'state_code', 'IL')
        domain_mapping = {v: k for k, v in settings.STATE_DOMAIN_MAPPING.items()}
        return domain_mapping.get(state_code, 'desiloginil.com')
    
    @staticmethod
    def _validate_email_config() -> bool:
        """Validate email configuration."""
        if not settings.EMAIL_HOST_USER:
            logger.error("EMAIL_HOST_USER is not configured")
            return False
        
        if not settings.EMAIL_HOST_PASSWORD:
            logger.error("EMAIL_HOST_PASSWORD is not configured")
            return False
        
        if settings.EMAIL_HOST == 'localhost':
            logger.warning("EMAIL_HOST is set to localhost - emails may not be delivered")
        
        return True
    
    @staticmethod
    def send_email(
        subject: str,
        recipient_list: List[str],
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None,
        fail_silently: bool = False
    ) -> bool:
        """
        Send email using HTML template with automatic text conversion.
        
        Args:
            subject: Email subject
            recipient_list: List of recipient emails
            template_name: Template name (without .html extension)
            context: Template context variables
            from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
            fail_silently: Whether to suppress exceptions
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Validate email configuration
            if not EmailService._validate_email_config():
                if not fail_silently:
                    raise Exception("Email configuration is incomplete")
                return False
            
            # Set default from_email
            if not from_email:
                from_email = settings.DEFAULT_FROM_EMAIL
            
            # Render HTML template
            try:
                html_message = render_to_string(f'emails/{template_name}.html', context)
                logger.debug(f"HTML template emails/{template_name}.html rendered successfully")
            except Exception as e:
                logger.error(f"Failed to render template emails/{template_name}.html: {e}")
                if not fail_silently:
                    raise Exception(f"Template not found: emails/{template_name}.html")
                return False
            
            # Generate text version by stripping HTML tags
            text_message = strip_tags(html_message)
            
            logger.info(f"Sending email to {recipient_list}")
            logger.debug(f"Subject: {subject}")
            logger.debug(f"Template: {template_name}")
            
            # Send email with both HTML and text versions
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=from_email,
                to=recipient_list
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=fail_silently)
            
            logger.info(f"Email sent successfully to {recipient_list}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            logger.error(f"Recipients: {recipient_list}, Subject: {subject}, Template: {template_name}")
            if not fail_silently:
                raise e
            return False

    @staticmethod
    def send_verification_email(user, request, verification_code: str) -> bool:
        """Send email verification code using email_verification template."""
        domain = EmailService._get_domain_from_request(request)
        
        context = {
            'user': user,
            'verification_code': verification_code,
            'domain': domain,
            'expires_in': 15,  # 15 minutes
        }
        
        return EmailService.send_email(
            subject=f'Email Verification Code for {domain}',
            recipient_list=[user.email],
            template_name='email_verification',
            context=context,
            fail_silently=True  # Don't break registration if email fails
        )
    
    @staticmethod
    def send_password_reset_email(user, request, reset_code: str) -> bool:
        """Send password reset code using password_reset template."""
        domain = EmailService._get_domain_from_request(request)
        
        context = {
            'user': user,
            'reset_code': reset_code,
            'domain': domain,
            'expires_in': 15,  # 15 minutes
        }
        
        return EmailService.send_email(
            subject=f'Password Reset Code for {domain}',
            recipient_list=[user.email],
            template_name='password_reset',
            context=context,
            fail_silently=True  # Don't reveal user existence for security
        )
    
# Convenience functions for easy import and use
def send_verification_email(user, request, verification_code: str) -> bool:
    """Send email verification code."""
    return EmailService.send_verification_email(user, request, verification_code)

def send_password_reset_email(user, request, reset_code: str) -> bool:
    """Send password reset code."""
    return EmailService.send_password_reset_email(user, request, reset_code)
