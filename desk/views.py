import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import HiddenInput
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, TicketForm, TicketUpdateForm
from .metrics import ticket_metrics
from .models import Category, Department, KnowledgeArticle, Ticket
from .permissions import is_support, visible_tickets
from .services import add_comment, claim_ticket, open_ticket, requester_action, update_ticket


def filter_tickets(qs, params, user):
    query = params.get("q", "").strip()[:200]
    if query:
        criteria = Q(title__icontains=query) | Q(description__icontains=query) | Q(equipment__icontains=query)
        reference_id = query.rsplit("-", 1)[-1]
        if reference_id.isdigit() and len(reference_id) < 12:
            criteria |= Q(pk=int(reference_id))
        qs = qs.filter(criteria)
    for field, choices in (("status", Ticket.Status.values), ("priority", Ticket.Priority.values), ("kind", Ticket.Kind.values)):
        if params.get(field) in choices:
            qs = qs.filter(**{field: params[field]})
    if params.get("status") == "active":
        qs = qs.exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    if params.get("status") == "finished":
        qs = qs.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    for field in ("category", "department"):
        value = params.get(field, "")
        if value.isdigit() and len(value) < 12:
            qs = qs.filter(**{f"{field}_id": int(value)})
    if params.get("mine") == "1" and is_support(user):
        qs = qs.filter(assigned_to=user)
    if params.get("unassigned") == "1" and is_support(user):
        qs = qs.filter(assigned_to__isnull=True).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    return qs


@login_required
def dashboard(request):
    tickets = visible_tickets(request.user)
    return render(request, "desk/dashboard.html", {
        "metrics": ticket_metrics(tickets),
        "recent_tickets": tickets[:6],
    })


@login_required
def ticket_list(request):
    scoped = visible_tickets(request.user)
    tickets = filter_tickets(scoped, request.GET, request.user)
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "desk/ticket_list.html", {
        "page_obj": Paginator(tickets, 15).get_page(request.GET.get("page")),
        "statuses": Ticket.Status.choices,
        "priorities": Ticket.Priority.choices,
        "kinds": Ticket.Kind.choices,
        "queue_counts": {
            "total": scoped.count(),
            "active": scoped.exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count(),
            "questions": scoped.filter(kind=Ticket.Kind.QUESTION).count(),
            "unassigned": scoped.filter(assigned_to__isnull=True).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count(),
        },
        "categories": Category.objects.all(),
        "departments": Department.objects.all(),
        "filter_query": params.urlencode(),
    })


def _attach_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            for message in errors:
                form.add_error(field if field in form.fields else None, message)
    else:
        form.add_error(None, error)


@login_required
def ticket_create(request, question=False):
    profile = getattr(request.user, "desk_profile", None)
    initial = {"department": profile.department_id} if profile else {}
    if question:
        initial.update(kind=Ticket.Kind.QUESTION, priority=Ticket.Priority.LOW)
    source = None
    source_id = request.GET.get("article", "")
    if source_id.isdigit() and len(source_id) < 12:
        source = get_object_or_404(KnowledgeArticle, pk=int(source_id), published=True)
        initial.update(source_article=source, title=f"Dúvida sobre: {source.title}"[:160])
        if source.category_id and source.category.active:
            initial["category"] = source.category_id
    form = TicketForm(request.POST if request.method == "POST" else None, initial=initial)
    if question:
        form.fields["kind"].widget = HiddenInput()
        form.fields["kind"].disabled = True
        form.fields.pop("equipment")
        form.fields["title"].label = "Assunto da dúvida"
        form.fields["title"].widget.attrs["placeholder"] = "Ex.: como solicitar acesso ao sistema?"
        form.fields["description"].label = "Sua dúvida"
        form.fields["description"].widget.attrs["placeholder"] = "Explique o que você precisa saber e quais orientações já consultou."
    if request.method == "POST" and form.is_valid():
        try:
            ticket = open_ticket(request.user, form.cleaned_data)
        except ValidationError as error:
            _attach_errors(form, error)
        else:
            messages.success(request, f"{ticket.reference} aberto. A equipe de TI acompanhará sua solicitação.")
            return redirect("ticket_detail", pk=ticket.pk)
    return render(request, "desk/ticket_form.html", {
        "form": form, "question_mode": question, "source_article": source,
        "suggested_articles": KnowledgeArticle.objects.filter(published=True, featured=True)[:3],
    })


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(visible_tickets(request.user), pk=pk)
    support = is_support(request.user)
    comment_form = CommentForm(support=support)
    update_form = TicketUpdateForm(instance=ticket) if support else None
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "comment":
            comment_form = CommentForm(request.POST, support=support)
            if comment_form.is_valid():
                try:
                    if request.POST.get("internal") and not support:
                        raise PermissionDenied
                    add_comment(request.user, ticket, comment_form.cleaned_data["body"], comment_form.cleaned_data.get("internal", False))
                except ValidationError as error:
                    _attach_errors(comment_form, error)
                else:
                    messages.success(request, "Mensagem registrada.")
                    return redirect("ticket_detail", pk=pk)
        elif action == "update":
            if not support:
                raise PermissionDenied
            update_form = TicketUpdateForm(request.POST, instance=ticket)
            if update_form.is_valid():
                try:
                    update_ticket(request.user, ticket, update_form.cleaned_data, update_form.cleaned_data["version"])
                except ValidationError as error:
                    _attach_errors(update_form, error)
                else:
                    messages.success(request, "Atendimento atualizado.")
                    return redirect("ticket_detail", pk=pk)
            # ModelForm altera sua instância ao validar; a leitura deve refletir o banco.
            ticket = get_object_or_404(visible_tickets(request.user), pk=pk)
    comments = ticket.comments.select_related("author")
    if not support:
        comments = comments.filter(internal=False)
    return render(request, "desk/ticket_detail.html", {
        "ticket": ticket, "comments_list": comments,
        "events": ticket.events.select_related("actor"),
        "comment_form": comment_form, "update_form": update_form,
    })


@login_required
@require_POST
def ticket_action(request, pk, action):
    ticket = get_object_or_404(visible_tickets(request.user), pk=pk)
    try:
        version = int(request.POST.get("version", "0"))
    except ValueError:
        version = 0
    try:
        if action == "claim":
            claim_ticket(request.user, ticket, version)
        else:
            requester_action(request.user, ticket, action, version)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        text = {"claim": "Chamado atribuído a você. Atualize o atendimento quando iniciar o trabalho.", "close": "Chamado encerrado.", "reopen": "Chamado devolvido à triagem."}
        messages.success(request, text.get(action, "Chamado atualizado."))
    return redirect("ticket_detail", pk=pk)


@login_required
def reports(request):
    if not is_support(request.user):
        raise PermissionDenied
    qs = visible_tickets(request.user)
    return render(request, "desk/reports.html", {"metrics": ticket_metrics(qs)})


def _csv_safe(value):
    text = str(value or "")
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


@login_required
def ticket_export(request):
    if not is_support(request.user):
        raise PermissionDenied
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="chamados.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Protocolo", "Assunto", "Tipo", "Unidade", "Categoria", "Prioridade", "Situação", "Solicitante", "Responsável", "Equipamento", "Abertura", "Primeira resposta", "Resolução", "Encerramento"])
    qs = filter_tickets(visible_tickets(request.user), request.GET, request.user)
    for ticket in qs.iterator():
        writer.writerow([_csv_safe(value) for value in [
            ticket.reference, ticket.title, ticket.get_kind_display(), ticket.department,
            ticket.category, ticket.get_priority_display(), ticket.get_status_display(),
            ticket.requester.get_full_name() or ticket.requester.username,
            str(ticket.assigned_to or ""), ticket.equipment, ticket.created_at.isoformat(),
            ticket.first_response_at.isoformat() if ticket.first_response_at else "",
            ticket.resolved_at.isoformat() if ticket.resolved_at else "",
            ticket.closed_at.isoformat() if ticket.closed_at else "",
        ]])
    return response
