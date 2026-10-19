from django.apps import AppConfig


class DeskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "desk"
    verbose_name = "Service Desk"

    def ready(self):
        from . import signals  # noqa: F401
