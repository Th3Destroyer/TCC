from django.contrib.auth import get_user_model
from django.db.models import Q

TECHNICIAN_GROUP = "Técnicos"
MANAGER_GROUP = "Gestores"


def is_manager(user):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or user.groups.filter(name=MANAGER_GROUP).exists()
    )


def is_support(user):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or user.groups.filter(name__in=[TECHNICIAN_GROUP, MANAGER_GROUP]).exists()
    )


def support_users():
    return get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=[TECHNICIAN_GROUP, MANAGER_GROUP])
    ).distinct().order_by("first_name", "username")


def visible_tickets(user):
    from .models import Ticket

    qs = Ticket.objects.select_related("requester", "assigned_to", "category", "department", "source_article")
    if not user.is_authenticated or not user.is_active:
        return qs.none()
    return qs if is_support(user) else qs.filter(requester=user)


def visible_articles(user):
    from .models import KnowledgeArticle

    qs = KnowledgeArticle.objects.select_related("category", "author", "updated_by")
    if not user.is_authenticated or not user.is_active:
        return qs.none()
    return qs if is_support(user) else qs.filter(published=True)
