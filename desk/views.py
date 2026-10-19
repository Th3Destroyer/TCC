import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, TicketForm, TicketUpdateForm
from .metrics import ticket_metrics
from .models import Category, Department, Ticket
from .permissions import is_support, visible_tickets
from .services import add_comment, open_ticket, requester_action, update_ticket


def filter_tickets(qs, params, user):
    query = params.get("q", "").strip()[:200]
    if query:
        criteria = Q(title__icontains=query) | Q(description__icontains=query) | Q(equipment__icontains=query)
        reference_id = query.rsplit("-", 1)[-1]
        if reference_id.isdigit() and len(reference_id) < 12:
            criteria |= Q(pk=int(reference_id))
        qs = qs.filter(criteria)
    for field, choices in (("status", Ticket.Status.values), ("priority", Ticket.Priority.values)):
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
    tickets = filter_tickets(visible_tickets(request.user), request.GET, request.user)
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "desk/ticket_list.html", {
        "page_obj": Paginator(tickets, 15).get_page(request.GET.get("page")),
        "statuses": Ticket.Status.choices,
        "priorities": Ticket.Priority.choices,
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
def ticket_create(request):
    profile = getattr(request.user, "desk_profile", None)
    initial = {"department": profile.department_id} if profile else {}
    form = TicketForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            ticket = open_ticket(request.user, form.cleaned_data)
        except ValidationError as error:
            _attach_errors(form, error)
        else:
            messages.success(request, f"{ticket.reference} aberto. A equipe de TI acompanhará sua solicitação.")
            return redirect("ticket_detail", pk=ticket.pk)
    return render(request, "desk/ticket_form.html", {"form": form})


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
        requester_action(request.user, ticket, action, version)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Chamado encerrado." if action == "close" else "Chamado devolvido à triagem.")
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
