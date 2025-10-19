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
    """Handle message creation - send notifications."""
    
    if created:
        # Don't send notification for system messages
        if instance.message_type == 'system':
            return
        
        # Get recipient
        conversation = instance.conversation
        recipient = conversation.get_other_user(instance.sender)
        
        # Send message notification
        NotificationService.send_new_message_notification(
            recipient=recipient,
            sender=instance.sender,
            message=instance,
            conversation=conversation
        )
        
        logger.info(
            f"Message notification sent: {instance.sender.email} -> {recipient.email}"
        )