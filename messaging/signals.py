# messaging/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Conversation, Message
from .services import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Conversation)
def conversation_created(sender, instance, created, **kwargs):
    """Send notification when a new conversation is created."""
    
    if created:
        NotificationService.send_new_conversation_notification(
            recipient=instance.seller,
            sender=instance.buyer,
            conversation=instance
        )
        
        logger.info(
            f"New conversation notification sent: {instance.buyer.email} -> {instance.seller.email}"
        )


@receiver(post_save, sender=Message)
def message_created(sender, instance, created, **kwargs):
    """Handle message creation - update conversation timestamp ONLY on creation."""
    
    # CRITICAL: Only update on creation, not on every save (like marking as read)
    if created and instance.message_type != 'system':
        # Update conversation's last_message_at timestamp
        conversation = instance.conversation
        
        # Only update if this message is newer than current last_message_at
        # This prevents race conditions with concurrent message sends
        if not conversation.last_message_at or instance.created_at > conversation.last_message_at:
            conversation.last_message_at = instance.created_at
            conversation.save(update_fields=['last_message_at'])
            
            logger.info(
                f"Message created: {instance.sender.email} in conversation {conversation.id}, "
                f"updated last_message_at to {instance.created_at}"
            )
        else:
            logger.info(
                f"Message created: {instance.sender.email} in conversation {conversation.id}, "
                f"but last_message_at not updated (older message)"
            )
        
        # NOTE: Notification is sent from the view to avoid duplicate notifications
        # and to ensure proper response timing