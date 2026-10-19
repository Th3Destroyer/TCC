from django.conf import settings
from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField("unidade / secretaria", max_length=120, unique=True)
    active = models.BooleanField("ativa", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "unidade administrativa"
        verbose_name_plural = "unidades administrativas"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("categoria", max_length=80, unique=True)
    active = models.BooleanField("ativa", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="desk_profile")
    department = models.ForeignKey(Department, verbose_name="unidade", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return str(self.user)


class Ticket(models.Model):
    class Kind(models.TextChoices):
        INCIDENT = "incident", "Incidente"
        REQUEST = "request", "Requisição de serviço"

    class Status(models.TextChoices):
        OPEN = "open", "Aberto"
        TRIAGE = "triage", "Em triagem"
        IN_PROGRESS = "in_progress", "Em atendimento"
        WAITING = "waiting", "Aguardando retorno"
        RESOLVED = "resolved", "Resolvido"
        CLOSED = "closed", "Encerrado"

    class Priority(models.TextChoices):
        LOW = "low", "Baixa"
        MEDIUM = "medium", "Média"
        HIGH = "high", "Alta"
        CRITICAL = "critical", "Crítica"

    title = models.CharField("assunto", max_length=160)
    description = models.TextField("descrição", max_length=10000)
    kind = models.CharField("tipo", max_length=16, choices=Kind.choices, default=Kind.INCIDENT)
    category = models.ForeignKey(Category, verbose_name="categoria", on_delete=models.PROTECT)
    department = models.ForeignKey(Department, verbose_name="unidade / secretaria", on_delete=models.PROTECT)
    equipment = models.CharField("equipamento / patrimônio", max_length=100, blank=True)
    priority = models.CharField("prioridade", max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField("situação", max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="solicitante", on_delete=models.PROTECT, related_name="requested_tickets")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="técnico responsável", on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_tickets")
    resolution = models.TextField("solução aplicada", max_length=10000, blank=True)
    created_at = models.DateTimeField("aberto em", default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    first_response_at = models.DateTimeField("primeira resposta técnica", null=True, blank=True, editable=False)
    resolved_at = models.DateTimeField("resolvido em", null=True, blank=True, editable=False)
    closed_at = models.DateTimeField("encerrado em", null=True, blank=True, editable=False)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "chamado"
        verbose_name_plural = "chamados"

    @property
    def reference(self):
        return f"SD-{timezone.localtime(self.created_at).year}-{self.pk:05d}"

    @property
    def is_finished(self):
        return self.status in (self.Status.RESOLVED, self.Status.CLOSED)

    def __str__(self):
        return f"{self.reference} · {self.title}"


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField("mensagem", max_length=10000)
    internal = models.BooleanField("nota interna", default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at", "pk"]
        verbose_name = "mensagem"
        verbose_name_plural = "mensagens"


class TicketEvent(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    message = models.TextField("evento")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "evento de chamado"
        verbose_name_plural = "histórico de chamados"
