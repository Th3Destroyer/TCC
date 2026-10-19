from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import decorators, exceptions, permissions, response, serializers, viewsets

from .metrics import ticket_metrics
from .models import Category, Comment, Department, KnowledgeArticle, Ticket, TicketEvent
from .permissions import is_support, support_users, visible_tickets
from .services import add_comment, claim_ticket, open_ticket, requester_action, update_ticket
from .help_views import filter_articles
from .views import filter_tickets


def call_service(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except DjangoValidationError as error:
        raise exceptions.ValidationError(error.message_dict if hasattr(error, "message_dict") else error.messages) from error


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "active"]


class DepartmentSerializer(CatalogSerializer):
    class Meta(CatalogSerializer.Meta):
        model = Department


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    class Meta:
        model = Comment
        fields = ["id", "author_name", "body", "internal", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]


class EventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() or obj.actor.username

    class Meta:
        model = TicketEvent
        fields = ["id", "actor_name", "message", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    reference = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    requester_name = serializers.SerializerMethodField()
    assigned_name = serializers.SerializerMethodField()
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(active=True))
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.filter(active=True))
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=support_users(), allow_null=True, required=False)
    version = serializers.IntegerField(required=False, min_value=1)
    source_article = serializers.PrimaryKeyRelatedField(queryset=KnowledgeArticle.objects.filter(published=True), required=False, allow_null=True)

    def get_requester_name(self, obj):
        return obj.requester.get_full_name() or obj.requester.username

    def get_assigned_name(self, obj):
        return (obj.assigned_to.get_full_name() or obj.assigned_to.username) if obj.assigned_to else None

    class Meta:
        model = Ticket
        fields = ["id", "reference", "title", "description", "kind", "category", "category_name", "department", "department_name", "equipment", "priority", "status", "status_label", "requester", "requester_name", "assigned_to", "assigned_name", "resolution", "source_article", "created_at", "updated_at", "first_response_at", "resolved_at", "closed_at", "version"]
        read_only_fields = ["id", "requester", "created_at", "updated_at", "first_response_at", "resolved_at", "closed_at"]

    def validate(self, attrs):
        if not self.instance:
            forbidden = {"status", "assigned_to", "resolution", "requester", "version"} & self.initial_data.keys()
            if forbidden:
                raise serializers.ValidationError("Situação, responsável e solução são definidos após a abertura pela equipe de TI.")
        else:
            if not is_support(self.context["request"].user):
                raise exceptions.PermissionDenied("Somente a equipe de TI pode editar o atendimento.")
            if "version" not in attrs:
                raise serializers.ValidationError({"version": "Informe a versão atual do chamado para evitar perda de alterações."})
            forbidden = set(self.initial_data) - {"version", "kind", "category", "department", "priority", "assigned_to", "status", "resolution"}
            if forbidden:
                raise serializers.ValidationError("Nesta etapa, edite somente a classificação e os dados de atendimento.")
        return attrs

    def create(self, validated_data):
        return call_service(open_ticket, self.context["request"].user, validated_data)

    def update(self, instance, validated_data):
        version = validated_data.pop("version")
        return call_service(update_ticket, self.context["request"].user, instance, validated_data, version)


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = visible_tickets(self.request.user)
        return filter_tickets(qs, self.request.query_params, self.request.user) if self.action == "list" else qs

    @decorators.action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            comment = call_service(add_comment, request.user, ticket, **serializer.validated_data)
            return response.Response(CommentSerializer(comment).data, status=201)
        qs = ticket.comments.select_related("author")
        if not is_support(request.user):
            qs = qs.filter(internal=False)
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(CommentSerializer(page, many=True).data)

    @decorators.action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        page = self.paginate_queryset(self.get_object().events.select_related("actor"))
        return self.get_paginated_response(EventSerializer(page, many=True).data)

    def _requester_action(self, request, action):
        version = request.data.get("version")
        if type(version) is not int or version < 1:
            raise exceptions.ValidationError({"version": "Informe a versão atual como inteiro positivo."})
        ticket = call_service(requester_action, request.user, self.get_object(), action, version)
        return response.Response(self.get_serializer(ticket).data)

    @decorators.action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        version = request.data.get("version")
        if type(version) is not int or version < 1:
            raise exceptions.ValidationError({"version": "Informe a versão atual como inteiro positivo."})
        ticket = call_service(claim_ticket, request.user, self.get_object(), version)
        return response.Response(self.get_serializer(ticket).data)

    @decorators.action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._requester_action(request, "close")

    @decorators.action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._requester_action(request, "reopen")


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(active=True)
    serializer_class = CatalogSerializer


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.filter(active=True)
    serializer_class = DepartmentSerializer


class ArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", default="Orientações gerais", read_only=True)

    class Meta:
        model = KnowledgeArticle
        fields = ["id", "title", "summary", "body", "category", "category_name", "featured", "updated_at"]


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        qs = KnowledgeArticle.objects.filter(published=True).select_related("category")
        return filter_articles(qs, self.request.query_params) if self.action == "list" else qs


@decorators.api_view(["GET"])
@decorators.permission_classes([permissions.IsAuthenticated])
def metrics(request):
    if not is_support(request.user):
        raise exceptions.PermissionDenied("Indicadores globais são exclusivos da equipe de TI.")
    return response.Response(ticket_metrics(visible_tickets(request.user)))
