from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import api, views

router = DefaultRouter()
router.register("tickets", api.TicketViewSet, basename="api-ticket")
router.register("categories", api.CategoryViewSet)
router.register("departments", api.DepartmentViewSet)

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("chamados/", views.ticket_list, name="ticket_list"),
    path("chamados/novo/", views.ticket_create, name="ticket_create"),
    path("chamados/exportar/", views.ticket_export, name="ticket_export"),
    path("chamados/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("chamados/<int:pk>/<str:action>/", views.ticket_action, name="ticket_action"),
    path("indicadores/", views.reports, name="reports"),
    path("api/metrics/", api.metrics, name="api-metrics"),
    path("api/", include(router.urls)),
]
