from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone

from .models import Ticket


def ticket_metrics(qs):
    averages = qs.aggregate(
        response=Avg(ExpressionWrapper(F("first_response_at") - F("created_at"), output_field=DurationField())),
        resolution=Avg(ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField())),
    )
    active = qs.exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    today = timezone.localdate()
    days = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        days.append({"label": day.strftime("%d/%m"), "count": qs.filter(created_at__date=day).count()})
    max_count = max((day["count"] for day in days), default=0) or 1
    for day in days:
        day["height"] = max(3, round(day["count"] / max_count * 100))
    return {
        "total": qs.count(),
        "active": active.count(),
        "in_progress": qs.filter(status=Ticket.Status.IN_PROGRESS).count(),
        "resolved": qs.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count(),
        "critical": active.filter(priority=Ticket.Priority.CRITICAL).count(),
        "response_hours": round(averages["response"].total_seconds() / 3600, 1) if averages["response"] is not None else None,
        "resolution_hours": round(averages["resolution"].total_seconds() / 3600, 1) if averages["resolution"] is not None else None,
        "response_samples": qs.filter(first_response_at__isnull=False).count(),
        "resolution_samples": qs.filter(resolved_at__isnull=False).count(),
        "categories": list(qs.values("category__name").annotate(count=Count("id")).order_by("-count", "category__name")),
        "departments": list(qs.values("department__name").annotate(count=Count("id")).order_by("-count", "department__name")[:6]),
        "equipment": list(qs.exclude(equipment="").values("equipment").annotate(count=Count("id")).filter(count__gt=1).order_by("-count", "equipment")[:6]),
        "days": days,
    }
