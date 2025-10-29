# messaging/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta

from .models import Conversation, Message, Notification
from .serializers import (
    ConversationSerializer,
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    NotificationSerializer,
    MessageStatsSerializer,
)
from .services import NotificationService
from core.pagination import StandardResultsSetPagination

import logging

logger = logging.getLogger(__name__)


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing conversations."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return ConversationCreateSerializer
        elif self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer

    def get_queryset(self):
        """Get conversations for the current user."""
        user = self.request.user

        queryset = (
            Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related(
                "buyer", "seller", "ad", "ad__category", "ad__city", "ad__state"
            )
            .prefetch_related("messages")
            .distinct()
        )

        # Skip status filtering for action endpoints that need to access any conversation
        if self.action in ["block", "unblock", "archive", "unarchive"]:
            ad_id = self.request.query_params.get("ad_id")
            if ad_id:
                queryset = queryset.filter(ad_id=ad_id)

            search = self.request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    Q(buyer__first_name__icontains=search)
                    | Q(buyer__last_name__icontains=search)
                    | Q(seller__first_name__icontains=search)
                    | Q(seller__last_name__icontains=search)
                    | Q(ad__title__icontains=search)
                )

            return queryset.order_by("-last_message_at", "-created_at")

        # Filter by status for list and retrieve actions
        status_filter = self.request.query_params.get("status", "active")
        if status_filter == "active":
            queryset = queryset.filter(is_active=True, is_blocked=False)
        elif status_filter == "blocked":
            queryset = queryset.filter(is_blocked=True)
        elif status_filter == "archived":
            queryset = queryset.filter(is_active=False)

        ad_id = self.request.query_params.get("ad_id")
        if ad_id:
            queryset = queryset.filter(ad_id=ad_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(buyer__first_name__icontains=search)
                | Q(buyer__last_name__icontains=search)
                | Q(seller__first_name__icontains=search)
                | Q(seller__last_name__icontains=search)
                | Q(ad__title__icontains=search)
            )

        return queryset.order_by("-last_message_at", "-created_at")

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a conversation and mark messages as read."""
        instance = self.get_object()

        # Mark all messages as read for the current user
        instance.mark_as_read(request.user)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        """Block a user - blocks ALL conversations with this user."""
        conversation = self.get_object()

        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {"error": "You are not a participant in this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get the other user in this conversation
        other_user = conversation.get_other_user(request.user)

        # Block ALL conversations with this user
        blocked_conversations = Conversation.objects.filter(
            Q(buyer=request.user, seller=other_user)
            | Q(buyer=other_user, seller=request.user)
        )

        blocked_count = blocked_conversations.update(
            is_blocked=True, blocked_by=request.user
        )

        return Response(
            {
                "message": f"User blocked successfully. {blocked_count} conversation(s) blocked.",
                "blocked_count": blocked_count,
                "blocked_user_id": other_user.id,
                "blocked_user_name": other_user.get_full_name(),
            }
        )

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        """Unblock a user - unblocks ALL conversations with this user."""
        conversation = self.get_object()

        if conversation.blocked_by != request.user:
            return Response(
                {"error": "Only the user who blocked can unblock this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get the other user
        other_user = conversation.get_other_user(request.user)

        # Unblock ALL conversations with this user that were blocked by current user
        unblocked_conversations = Conversation.objects.filter(
            Q(buyer=request.user, seller=other_user)
            | Q(buyer=other_user, seller=request.user),
            blocked_by=request.user,
        )

        unblocked_count = unblocked_conversations.update(
            is_blocked=False, blocked_by=None
        )

        return Response(
            {
                "message": f"User unblocked successfully. {unblocked_count} conversation(s) unblocked.",
                "unblocked_count": unblocked_count,
                "unblocked_user_id": other_user.id,
                "unblocked_user_name": other_user.get_full_name(),
            }
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archive a conversation."""
        conversation = self.get_object()

        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {"error": "You are not a participant in this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        conversation.is_active = False
        conversation.save()

        return Response({"message": "Conversation archived successfully."})

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        """Unarchive a conversation."""
        conversation = self.get_object()

        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {"error": "You are not a participant in this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        conversation.is_active = True
        conversation.save()

        return Response(
            {
                "message": "Conversation restored successfully.",
                "conversation": ConversationSerializer(
                    conversation, context={"request": request}
                ).data,
            }
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get total unread message count."""
        user = request.user

        unread_count = (
            Message.objects.filter(
                conversation__in=Conversation.objects.filter(
                    Q(buyer=user) | Q(seller=user)
                ),
                is_read=False,
            )
            .exclude(sender=user)
            .count()
        )

        return Response({"unread_count": unread_count})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get messaging statistics for the current user."""
        user = request.user

        conversations = Conversation.objects.filter(Q(buyer=user) | Q(seller=user))

        sent_messages = Message.objects.filter(sender=user).count()

        received_messages = (
            Message.objects.filter(conversation__in=conversations)
            .exclude(sender=user)
            .count()
        )

        unread = (
            Message.objects.filter(conversation__in=conversations, is_read=False)
            .exclude(sender=user)
            .count()
        )

        stats = {
            "total_conversations": conversations.count(),
            "active_conversations": conversations.filter(
                is_active=True, is_blocked=False
            ).count(),
            "total_messages_sent": sent_messages,
            "total_messages_received": received_messages,
            "unread_messages": unread,
        }

        serializer = MessageStatsSerializer(stats)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing messages."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        """Get messages for the current user."""
        user = self.request.user

        user_conversations = Conversation.objects.filter(Q(buyer=user) | Q(seller=user))

        queryset = (
            Message.objects.filter(conversation__in=user_conversations)
            .select_related("sender", "conversation", "conversation__ad")
            .order_by("-created_at")
        )

        conversation_id = self.request.query_params.get("conversation_id")
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        message_type = self.request.query_params.get("type")
        if message_type:
            queryset = queryset.filter(message_type=message_type)

        if self.request.query_params.get("unread") == "true":
            queryset = queryset.filter(is_read=False).exclude(sender=user)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new message."""
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()

        # Get conversation and recipient
        conversation = message.conversation
        recipient = conversation.get_other_user(request.user)

        # Send notification (email will be sent asynchronously in background)
        try:
            NotificationService.send_new_message_notification(
                recipient=recipient,
                sender=request.user,
                message=message,
                conversation=conversation,
            )
        except Exception as e:
            # Log error but don't fail the message creation
            logger.error(f"Failed to send notification: {str(e)}")

        # Return response immediately without waiting for email
        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark a message as read."""
        message = self.get_object()

        if message.sender == request.user:
            return Response(
                {"error": "You cannot mark your own message as read."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message.mark_as_read()

        return Response(
            {
                "message": "Message marked as read.",
                "data": MessageSerializer(message, context={"request": request}).data,
            }
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all messages in a conversation as read."""
        conversation_id = request.data.get("conversation_id")

        if not conversation_id:
            return Response(
                {"error": "conversation_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation = get_object_or_404(Conversation, id=conversation_id)

        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {"error": "You are not a participant in this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        updated_count = (
            Message.objects.filter(conversation=conversation, is_read=False)
            .exclude(sender=request.user)
            .update(is_read=True, read_at=timezone.now())
        )

        return Response({"message": f"{updated_count} messages marked as read."})

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        """Flag a message as inappropriate."""
        message = self.get_object()

        message.is_flagged = True
        message.save()

        return Response({"message": "Message flagged for review."})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing notifications."""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Get notifications for the current user."""
        queryset = (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("conversation", "ad")
            .order_by("-created_at")
        )

        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == "true")

        notif_type = self.request.query_params.get("type")
        if notif_type:
            queryset = queryset.filter(notification_type=notif_type)

        return queryset

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.mark_as_read()

        return Response(
            {
                "message": "Notification marked as read.",
                "data": NotificationSerializer(
                    notification, context={"request": request}
                ).data,
            }
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        updated_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({"message": f"{updated_count} notifications marked as read."})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get unread notification count."""
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        return Response({"unread_count": count})

    @action(detail=False, methods=["delete"])
    def clear_all(self, request):
        """Delete all read notifications."""
        deleted_count, _ = Notification.objects.filter(
            recipient=request.user, is_read=True
        ).delete()

        return Response({"message": f"{deleted_count} notifications cleared."})
