# messaging/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, Notification
from ads.serializers import AdListSerializer
from accounts.serializers import UserPublicSerializer
from django.utils.timesince import timesince
from django.db.models import Q  # <-- required for filtering blocked users

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages."""

    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "sender_name",
            "sender_avatar",
            "message_type",
            "content",
            "image",
            "is_read",
            "read_at",
            "is_flagged",
            "created_at",
            "time_ago",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_name",
            "sender_avatar",
            "created_at",
            "time_ago",
        ]

    def get_sender_avatar(self, obj):
        """Get sender's avatar URL."""
        if obj.sender.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.sender.avatar.url)
        return None

    def get_time_ago(self, obj):
        """Get human-readable time since message was sent."""
        return f"{timesince(obj.created_at)} ago"


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""

    class Meta:
        model = Message
        fields = ["conversation", "message_type", "content", "image"]

    def validate(self, data):
        """Validate message data."""
        message_type = data.get("message_type", "text")

        if message_type == "text" and not data.get("content"):
            raise serializers.ValidationError(
                {"content": "Text messages must have content."}
            )

        if message_type == "image" and not data.get("image"):
            raise serializers.ValidationError(
                {"image": "Image messages must include an image."}
            )

        conversation = data.get("conversation")
        if conversation and not conversation.is_active:
            raise serializers.ValidationError(
                {"conversation": "Cannot send messages to inactive conversations."}
            )

        if conversation and conversation.is_blocked:
            raise serializers.ValidationError(
                {"conversation": "This conversation has been blocked."}
            )

        return data

    def create(self, validated_data):
        """Create message."""
        validated_data["sender"] = self.context["request"].user
        message = Message.objects.create(**validated_data)
        return message


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations."""

    buyer = UserPublicSerializer(read_only=True)
    seller = UserPublicSerializer(read_only=True)
    ad = AdListSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "buyer",
            "seller",
            "ad",
            "is_active",
            "is_blocked",
            "created_at",
            "updated_at",
            "last_message_at",
            "last_message",
            "unread_count",
            "other_user",
        ]
        read_only_fields = [
            "id",
            "buyer",
            "seller",
            "created_at",
            "updated_at",
            "last_message_at",
        ]

    def get_last_message(self, obj):
        """Get the last message in this conversation."""
        # Use order_by to ensure we get the actual last message
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        """Get unread message count for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0

    def get_other_user(self, obj):
        """Get the other participant in this conversation."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            other = obj.get_other_user(request.user)
            return UserPublicSerializer(other, context=self.context).data
        return None


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating conversations."""

    ad_id = serializers.IntegerField()
    initial_message = serializers.CharField(required=False, max_length=1000)

    def validate_ad_id(self, value):
        """Validate that the ad exists and is approved."""
        from ads.models import Ad

        try:
            ad = Ad.objects.get(id=value, status="approved")
        except Ad.DoesNotExist:
            raise serializers.ValidationError("Ad not found or not available.")

        return value

    # def create(self, validated_data):
    #     """Create conversation and optional initial message."""
    #     from ads.models import Ad
    #
    #     ad_id = validated_data['ad_id']
    #     initial_message_content = validated_data.get('initial_message')
    #
    #     ad = Ad.objects.get(id=ad_id)
    #     buyer = self.context['request'].user
    #     seller = ad.user
    #
    #     if buyer == seller:
    #         raise serializers.ValidationError({
    #             'ad_id': 'You cannot start a conversation with yourself.'
    #         })
    #
    #     conversation, created = Conversation.objects.get_or_create(
    #         buyer=buyer,
    #         seller=seller,
    #         ad=ad,
    #         defaults={'is_active': True, 'is_blocked': False}
    #     )
    #
    #     if not created and not conversation.is_active:
    #         conversation.is_active = True
    #         conversation.save()
    #
    #     if initial_message_content:
    #         Message.objects.create(
    #             conversation=conversation,
    #             sender=buyer,
    #             message_type='text',
    #             content=initial_message_content
    #         )
    #
    #     return conversation

    def create(self, validated_data):
        """Create conversation and optional initial message."""
        from ads.models import Ad

        ad_id = validated_data["ad_id"]
        initial_message_content = validated_data.get("initial_message")

        ad = Ad.objects.get(id=ad_id)
        buyer = self.context["request"].user
        seller = ad.user

        if buyer == seller:
            raise serializers.ValidationError(
                {"error": "You cannot start a conversation with yourself."}
            )

        # Check if either user has blocked the other
        existing_blocked = Conversation.objects.filter(
            Q(buyer=buyer, seller=seller) | Q(buyer=seller, seller=buyer),
            is_blocked=True,
        ).first()

        if existing_blocked:
            blocker = existing_blocked.blocked_by
            if blocker == buyer:
                raise serializers.ValidationError(
                    {
                        "error": "You have blocked this user. Please unblock them first to start a conversation."
                    }
                )
            else:
                raise serializers.ValidationError(
                    {
                        "error": "This user has blocked you. You cannot start a conversation with them."
                    }
                )

        conversation, created = Conversation.objects.get_or_create(
            buyer=buyer,
            seller=seller,
            ad=ad,
            defaults={"is_active": True, "is_blocked": False},
        )

        if not created and not conversation.is_active:
            conversation.is_active = True
            conversation.save()

        if initial_message_content:
            Message.objects.create(
                conversation=conversation,
                sender=buyer,
                message_type="text",
                content=initial_message_content,
            )

        return conversation


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single conversation with messages."""

    buyer = UserPublicSerializer(read_only=True)
    seller = UserPublicSerializer(read_only=True)
    ad = AdListSerializer(read_only=True)
    messages = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "buyer",
            "seller",
            "ad",
            "is_active",
            "is_blocked",
            "created_at",
            "updated_at",
            "last_message_at",
            "messages",
            "unread_count",
            "other_user",
        ]

    def get_messages(self, obj):
        """Get all messages in this conversation."""
        messages = obj.messages.order_by("created_at")
        return MessageSerializer(messages, many=True, context=self.context).data

    def get_unread_count(self, obj):
        """Get unread message count for current user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0

    def get_other_user(self, obj):
        """Get the other participant in this conversation."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            other = obj.get_other_user(request.user)
            return UserPublicSerializer(other, context=self.context).data
        return None


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""

    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "action_url",
            "is_read",
            "read_at",
            "created_at",
            "time_ago",
            "conversation",
            "ad",
        ]
        read_only_fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "action_url",
            "created_at",
            "time_ago",
        ]

    def get_time_ago(self, obj):
        """Get human-readable time since notification was created."""
        return f"{timesince(obj.created_at)} ago"


class MessageStatsSerializer(serializers.Serializer):
    """Serializer for message statistics."""

    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    total_messages_sent = serializers.IntegerField()
    total_messages_received = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
