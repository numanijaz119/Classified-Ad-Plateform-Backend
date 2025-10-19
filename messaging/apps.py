from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
    verbose_name = 'Messaging & Notifications'

    def ready(self):
        """Import signal handlers when app is ready."""
        import messaging.signals