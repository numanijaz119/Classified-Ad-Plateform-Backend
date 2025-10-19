# messaging/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Notification
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and sending notifications."""
    
    @staticmethod
    def create_notification(recipient, notification_type, title, message, **kwargs):
        """Create a notification for a user."""
        
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            conversation=kwargs.get('conversation'),
            ad=kwargs.get('ad'),
            action_url=kwargs.get('action_url'),
        )
        
        # Check which email preference to use based on notification type
        should_send_email = False
        
        if notification_type in ['new_message', 'new_conversation']:
            # For messaging notifications, check email_message_notifications
            should_send_email = recipient.email_message_notifications
        else:
            # For other notifications (ad updates, etc), check email_notifications
            should_send_email = recipient.email_notifications
        
        # Send email if preference is enabled
        if should_send_email and settings.NOTIFICATION_SETTINGS.get('EMAIL_NOTIFICATIONS', False):
            NotificationService._send_email_notification(notification, recipient)
        
        return notification
    
    @staticmethod
    def _send_email_notification(notification, recipient):
        """Send email notification."""
        
        try:
            # Prepare email context
            context = {
                'recipient_name': recipient.get_full_name(),
                'title': notification.title,
                'message': notification.message,
                'action_url': notification.action_url,
                'site_url': f"https://{settings.ALLOWED_HOSTS[0]}" if settings.ALLOWED_HOSTS else 'http://localhost:5173',
            }
            
            # Render email template
            html_message = render_to_string(
                f'messaging/emails/{notification.notification_type}.html',
                context
            )
            plain_message = render_to_string(
                f'messaging/emails/{notification.notification_type}.txt',
                context
            )
            
            # Send email
            send_mail(
                subject=notification.title,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            notification.email_sent = True
            notification.save(update_fields=['email_sent'])
            
            logger.info(f"Email notification sent to {recipient.email}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    # Specific notification creators
    
    @staticmethod
    def send_new_message_notification(recipient, sender, message, conversation):
        """Send notification for new message."""
        
        title = f"New message from {sender.get_full_name()}"
        content = message.content[:100] + "..." if len(message.content) > 100 else message.content
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='new_message',
            title=title,
            message=content,
            conversation=conversation,
            ad=conversation.ad,
            action_url=f"/messages/{conversation.id}"
        )
    
    @staticmethod
    def send_new_conversation_notification(recipient, sender, conversation):
        """Send notification for new conversation."""
        
        title = f"{sender.get_full_name()} is interested in your ad"
        message_text = f"{sender.get_full_name()} started a conversation about '{conversation.ad.title}'"
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='new_conversation',
            title=title,
            message=message_text,
            conversation=conversation,
            ad=conversation.ad,
            action_url=f"/messages/{conversation.id}"
        )
    
    @staticmethod
    def send_ad_approved_notification(recipient, ad):
        """Send notification when ad is approved."""
        
        title = "Your ad has been approved!"
        message_text = f"Your ad '{ad.title}' has been approved and is now live."
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='ad_approved',
            title=title,
            message=message_text,
            ad=ad,
            action_url=f"/ads/{ad.slug}"
        )
    
    @staticmethod
    def send_ad_rejected_notification(recipient, ad, reason=None):
        """Send notification when ad is rejected."""
        
        title = "Your ad was not approved"
        message_text = f"Your ad '{ad.title}' was not approved."
        if reason:
            message_text += f" Reason: {reason}"
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='ad_rejected',
            title=title,
            message=message_text,
            ad=ad,
            action_url=f"/dashboard/my-ads"
        )
    
    @staticmethod
    def send_ad_expired_notification(recipient, ad):
        """Send notification when ad expires."""
        
        title = "Your ad has expired"
        message_text = f"Your ad '{ad.title}' has expired. You can renew it from your dashboard."
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='ad_expired',
            title=title,
            message=message_text,
            ad=ad,
            action_url=f"/dashboard/my-ads"
        )
    
    @staticmethod
    def send_ad_expiring_soon_notification(recipient, ad, days_left):
        """Send notification when ad is expiring soon."""
        
        title = f"Your ad expires in {days_left} days"
        message_text = f"Your ad '{ad.title}' will expire in {days_left} days. Renew it to keep it active."
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='ad_expiring_soon',
            title=title,
            message=message_text,
            ad=ad,
            action_url=f"/dashboard/my-ads"
        )
    
    @staticmethod
    def send_system_notification(recipient, title, message, action_url=None):
        """Send a system notification."""
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type='system',
            title=title,
            message=message,
            action_url=action_url
        )