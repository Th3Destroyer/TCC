from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Comment, Ticket, TicketEvent
from .permissions import is_support

S = Ticket.Status
TRANSITIONS = {
    S.OPEN: {S.TRIAGE, S.IN_PROGRESS},
    S.TRIAGE: {S.IN_PROGRESS, S.WAITING},
    S.IN_PROGRESS: {S.WAITING, S.RESOLVED},
    S.WAITING: {S.TRIAGE, S.IN_PROGRESS, S.RESOLVED},
    S.RESOLVED: {S.CLOSED, S.TRIAGE},
    S.CLOSED: {S.TRIAGE},
}


def _check_access(actor, ticket):
    if not actor.is_authenticated or not actor.is_active or not (
        is_support(actor) or ticket.requester_id == actor.pk
    ):
        raise PermissionDenied("Você não tem acesso a este chamado.")


@transaction.atomic
def open_ticket(actor, data):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied
    fields = {key: data[key] for key in (
        "title", "description", "kind", "category", "department", "equipment", "priority", "source_article"
    ) if key in data}
    if fields.get("source_article") and not fields["source_article"].published:
        raise ValidationError({"source_article": "Esta orientação não está publicada."})
    ticket = Ticket(requester=actor, **fields)
    ticket.full_clean()
    ticket.save()
    TicketEvent.objects.create(ticket=ticket, actor=actor, message="Chamado aberto.")
    return ticket


@transaction.atomic
def claim_ticket(actor, ticket, expected_version):
    if not is_support(actor):
        raise PermissionDenied("Somente a equipe de TI pode assumir chamados.")
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _check_version(ticket, expected_version)
    if ticket.is_finished:
        raise ValidationError("Reabra o chamado antes de assumir o atendimento.")
    if ticket.assigned_to_id and ticket.assigned_to_id != actor.pk:
        raise ValidationError("Este chamado já possui responsável. Atualize a página ou solicite o encaminhamento à equipe.")
    changes = {"assigned_to": actor}
    if ticket.status == S.OPEN:
        changes["status"] = S.TRIAGE
    return update_ticket(actor, ticket, changes, expected_version)


@transaction.atomic
def update_ticket(actor, ticket, changes, expected_version):
    if not is_support(actor):
        raise PermissionDenied("Somente a equipe de TI pode classificar ou encaminhar chamados.")
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _check_version(ticket, expected_version)
    old_status = ticket.status
    old_resolution = ticket.resolution
    new_status = changes.get("status", old_status)
    if new_status != old_status and new_status not in TRANSITIONS.get(old_status, set()):
        raise ValidationError({"status": "Transição inválida. Siga as etapas do atendimento."})
    fields = ("kind", "category", "department", "priority", "assigned_to", "status", "resolution")
    summary = []
    for field in fields:
        if field not in changes:
            continue
        new_value = changes[field]
        old_value = getattr(ticket, field)
        if new_value != old_value:
            model_field = Ticket._meta.get_field(field)
            display = getattr(ticket, f"get_{field}_display", None)
            old_label = display() if display else str(old_value or "Não definido")
            setattr(ticket, field, new_value)
            new_label = display() if display else str(new_value or "Não definido")
            summary.append(
                "Solução registrada/atualizada." if field == "resolution" else
                f"{str(model_field.verbose_name).capitalize()}: {old_label} → {new_label}."
            )
    if ticket.assigned_to and not is_support(ticket.assigned_to):
        raise ValidationError({"assigned_to": "Selecione um técnico ativo da equipe de TI."})
    if ticket.status in (S.IN_PROGRESS, S.WAITING, S.RESOLVED, S.CLOSED) and not ticket.assigned_to:
        raise ValidationError({"assigned_to": "Defina um responsável antes de iniciar o atendimento."})
    if ticket.status in (S.RESOLVED, S.CLOSED) and not ticket.resolution.strip():
        raise ValidationError({"resolution": "Descreva a solução antes de resolver o chamado."})
    if old_status in (S.RESOLVED, S.CLOSED) and new_status == S.TRIAGE:
        ticket.resolved_at = ticket.closed_at = None
        ticket.resolution = ""
        summary.append("Chamado reaberto; a solução anterior permanece no histórico de mensagens.")
    now = timezone.now()
    if old_status != new_status:
        if new_status in (S.IN_PROGRESS, S.RESOLVED) and not ticket.first_response_at:
            ticket.first_response_at = now
        if new_status == S.RESOLVED:
            ticket.resolved_at = now
        if new_status == S.CLOSED:
            ticket.closed_at = now
    if not summary:
        return ticket
    ticket.full_clean()
    _save_version(ticket)
    TicketEvent.objects.create(ticket=ticket, actor=actor, message="\n".join(summary))
    if new_status in (S.RESOLVED, S.CLOSED) and (
        old_status != new_status or old_resolution != ticket.resolution
    ):
        Comment.objects.create(ticket=ticket, author=actor, body=f"Solução aplicada:\n{ticket.resolution}")
    return ticket


def _check_version(ticket, expected_version):
    if expected_version != ticket.version:
        raise ValidationError("Este chamado foi atualizado por outra pessoa. Recarregue a página antes de salvar.")


def _save_version(ticket):
    previous = ticket.version
    ticket.version += 1
    # A condição também protege contra formulários obsoletos em bancos sem row locks.
    values = {field.attname: getattr(ticket, field.attname) for field in Ticket._meta.concrete_fields if field.name not in ("id", "updated_at")}
    values["updated_at"] = timezone.now()
    if Ticket.objects.filter(pk=ticket.pk, version=previous).update(**values) != 1:
        raise ValidationError("O chamado mudou durante a edição. Recarregue a página.")


@transaction.atomic
def add_comment(actor, ticket, body, internal=False):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _check_access(actor, ticket)
    if internal and not is_support(actor):
        raise PermissionDenied("Notas internas são exclusivas da equipe de TI.")
    if ticket.status == S.CLOSED:
        raise ValidationError("Reabra o chamado antes de enviar novas mensagens.")
    if not body.strip() or len(body) > 10000:
        raise ValidationError("Escreva uma mensagem de até 10.000 caracteres.")
    comment = Comment.objects.create(ticket=ticket, author=actor, body=body.strip(), internal=internal)
    if is_support(actor) and not internal and actor.pk != ticket.requester_id and not ticket.first_response_at:
        ticket.first_response_at = timezone.now()
    _save_version(ticket)
    return comment


@transaction.atomic
def requester_action(actor, ticket, action, expected_version):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _check_access(actor, ticket)
    _check_version(ticket, expected_version)
    if actor.pk != ticket.requester_id:
        raise PermissionDenied("Esta confirmação é exclusiva do solicitante.")
    if action == "close" and ticket.status == S.RESOLVED:
        ticket.status = S.CLOSED
        ticket.closed_at = timezone.now()
        message = "Solução confirmada pelo solicitante. Chamado encerrado."
    elif action == "reopen" and ticket.status in (S.RESOLVED, S.CLOSED):
        ticket.status = S.TRIAGE
        ticket.resolved_at = ticket.closed_at = None
        ticket.resolution = ""
        message = "Chamado reaberto pelo solicitante e devolvido à triagem."
    else:
        raise ValidationError("Esta ação não está disponível para a situação atual.")
    _save_version(ticket)
    TicketEvent.objects.create(ticket=ticket, actor=actor, message=message)
    return ticket
