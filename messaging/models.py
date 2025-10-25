from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from ads.models import Ad

User = get_user_model()


class Conversation(models.Model):
    """Model for conversations between users about an ad."""

    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="buyer_conversations",
        verbose_name=_("Buyer"),
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="seller_conversations",
        verbose_name=_("Seller"),
    )
    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name=_("Advertisement"),
    )

    is_active = models.BooleanField(_("Is Active"), default=True)
    is_blocked = models.BooleanField(_("Is Blocked"), default=False)
    blocked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_conversations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["buyer", "seller", "ad"]),
            models.Index(fields=["buyer", "-last_message_at"]),
            models.Index(fields=["seller", "-last_message_at"]),
            models.Index(fields=["-last_message_at"]),
        ]
        unique_together = [["buyer", "seller", "ad"]]

    def __str__(self):
        return f"Conversation: {self.buyer.get_full_name()} <-> {self.seller.get_full_name()} about {self.ad.title}"

    def get_other_user(self, user):
        """Get the other participant in this conversation."""
        return self.seller if user == self.buyer else self.buyer

    def get_unread_count(self, user):
        """Get unread message count for a specific user."""
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    def mark_as_read(self, user):
        """Mark all messages as read for a specific user."""
        self.messages.filter(is_read=False).exclude(sender=user).update(
            is_read=True, read_at=timezone.now()
        )


class Message(models.Model):
    """Model for messages within a conversation."""

    MESSAGE_TYPE_CHOICES = [
        ("text", "Text Message"),
        ("image", "Image"),
        ("system", "System Message"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Conversation"),
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name=_("Sender"),
    )

    message_type = models.CharField(
        _("Message Type"), max_length=20, choices=MESSAGE_TYPE_CHOICES, default="text"
    )
    content = models.TextField(_("Content"))
    image = models.ImageField(
        _("Image"), upload_to="messages/images/%Y/%m/", null=True, blank=True
    )

    is_read = models.BooleanField(_("Is Read"), default=False)
    read_at = models.DateTimeField(_("Read At"), null=True, blank=True)
    is_flagged = models.BooleanField(_("Is Flagged"), default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"Message from {self.sender.get_full_name()} at {self.created_at}"


def save(self, *args, **kwargs):
    """Override save to update conversation's last_message_at ONLY on creation."""
    is_new = self.pk is None
    super().save(*args, **kwargs)

    # CRITICAL: Only update last_message_at when creating NEW message
    # This prevents conversations from jumping when messages are marked as read
    if is_new:
        self.conversation.last_message_at = self.created_at
        self.conversation.save(update_fields=["last_message_at"])

    def mark_as_read(self):
        """Mark this message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class Notification(models.Model):
    """Model for user notifications."""

    NOTIFICATION_TYPE_CHOICES = [
        ("new_message", "New Message"),
        ("new_conversation", "New Conversation"),
        ("ad_approved", "Ad Approved"),
        ("ad_rejected", "Ad Rejected"),
        ("ad_expired", "Ad Expired"),
        ("ad_expiring_soon", "Ad Expiring Soon"),
        ("system", "System Notification"),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )

    notification_type = models.CharField(
        _("Notification Type"), max_length=30, choices=NOTIFICATION_TYPE_CHOICES
    )
    title = models.CharField(_("Title"), max_length=255)
    message = models.TextField(_("Message"))

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    action_url = models.CharField(
        _("Action URL"), max_length=500, null=True, blank=True
    )

    is_read = models.BooleanField(_("Is Read"), default=False)
    read_at = models.DateTimeField(_("Read At"), null=True, blank=True)
    email_sent = models.BooleanField(_("Email Sent"), default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.get_full_name()}: {self.title}"

    def mark_as_read(self):
        """Mark this notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
