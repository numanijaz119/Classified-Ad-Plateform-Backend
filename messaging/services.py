from django.conf import settings
from .models import Notification
from core.email_utils import EmailService
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
        """Send email notification using existing EmailService."""
        
        try:
            # Map notification types to template names
            template_map = {
                'new_message': 'messaging/new_message',
                'new_conversation': 'messaging/new_conversation',
                'ad_approved': 'messaging/ad_approved',
                'ad_rejected': 'messaging/ad_rejected',
                'ad_expired': 'messaging/ad_expired',
                'ad_expiring_soon': 'messaging/ad_expiring_soon',
                'system': 'messaging/system_notification',
            }
            
            template_name = template_map.get(notification.notification_type, 'messaging/generic')
            
            # Prepare context for email templates
            context = {
                'recipient_name': recipient.get_full_name(),
                'user': recipient,
                'title': notification.title,
                'message': notification.message,
                'notification': notification,
                'action_url': notification.action_url,
            }
            
            # Use existing EmailService to send email (maintains consistency)
            success = EmailService.send_email(
                subject=notification.title,
                recipient_list=[recipient.email],
                template_name=template_name,
                context=context,
                fail_silently=True  # Don't break app if email fails
            )
            
            if success:
                notification.email_sent = True
                notification.save(update_fields=['email_sent'])
                logger.info(f"Email notification sent to {recipient.email}")
            else:
                logger.warning(f"Failed to send email notification to {recipient.email}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
    
    # =========================================================================
    # SPECIFIC NOTIFICATION CREATORS
    # =========================================================================
    
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