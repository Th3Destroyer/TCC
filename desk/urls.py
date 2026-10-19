from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import api, help_views, views

router = DefaultRouter()
router.register("tickets", api.TicketViewSet, basename="api-ticket")
router.register("categories", api.CategoryViewSet)
router.register("departments", api.DepartmentViewSet)
router.register("articles", api.ArticleViewSet, basename="api-article")

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("chamados/", views.ticket_list, name="ticket_list"),
    path("chamados/novo/", views.ticket_create, name="ticket_create"),
    path("chamados/exportar/", views.ticket_export, name="ticket_export"),
    path("chamados/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("chamados/<int:pk>/<str:action>/", views.ticket_action, name="ticket_action"),
    path("indicadores/", views.reports, name="reports"),
    path("ajuda/", help_views.help_center, name="help_center"),
    path("ajuda/perguntar/", views.ticket_create, {"question": True}, name="question_create"),
    path("ajuda/gerenciar/", help_views.article_manage, name="article_manage"),
    path("ajuda/artigos/novo/", help_views.article_edit, name="article_create"),
    path("ajuda/artigos/<int:pk>/", help_views.article_detail, name="article_detail"),
    path("ajuda/artigos/<int:pk>/editar/", help_views.article_edit, name="article_edit"),
    path("ajuda/artigos/<int:pk>/avaliar/", help_views.article_feedback, name="article_feedback"),
    path("api/metrics/", api.metrics, name="api-metrics"),
    path("api/", include(router.urls)),
]
