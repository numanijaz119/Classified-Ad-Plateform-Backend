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
    """Handle message creation - update conversation timestamp."""
    
    if created:
        # Update conversation's last_message_at timestamp
        conversation = instance.conversation
        conversation.last_message_at = instance.created_at
        conversation.save(update_fields=['last_message_at'])
        
        logger.info(
            f"Message created: {instance.sender.email} in conversation {conversation.id}"
        )
        
        # NOTE: Notification is sent from the view to avoid duplicate notifications
        # and to ensure proper response timing