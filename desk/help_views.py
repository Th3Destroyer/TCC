from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ArticleForm
from .models import ArticleFeedback, Category, KnowledgeArticle, Ticket
from .permissions import is_support, visible_articles, visible_tickets


def filter_articles(qs, params):
    query = params.get("q", "").strip()[:200]
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query))
    category = params.get("category", "")
    if category == "general":
        qs = qs.filter(category__isnull=True)
    elif category.isdigit() and len(category) < 12:
        qs = qs.filter(category_id=int(category))
    return qs


@login_required
def help_center(request):
    published = KnowledgeArticle.objects.filter(published=True).select_related("category")
    articles = filter_articles(published, request.GET)
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "desk/help_center.html", {
        "page_obj": Paginator(articles, 9).get_page(request.GET.get("page")),
        "categories": Category.objects.filter(knowledgearticle__published=True).annotate(article_count=Count("knowledgearticle")),
        "general_count": published.filter(category__isnull=True).count(),
        "article_count": published.count(),
        "frequent_articles": published.filter(featured=True)[:5],
        "open_questions": visible_tickets(request.user).filter(kind=Ticket.Kind.QUESTION).exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count(),
        "filter_query": params.urlencode(),
    })


@login_required
def article_detail(request, pk):
    article = get_object_or_404(visible_articles(request.user), pk=pk)
    related = KnowledgeArticle.objects.filter(published=True, category=article.category).exclude(pk=pk)[:3]
    return render(request, "desk/article_detail.html", {
        "article": article,
        "my_feedback": ArticleFeedback.objects.filter(article=article, user=request.user).first(),
        "related_articles": related,
    })


@login_required
@require_POST
def article_feedback(request, pk):
    article = get_object_or_404(KnowledgeArticle, pk=pk, published=True)
    choice = request.POST.get("helpful")
    if choice not in ("yes", "no"):
        messages.error(request, "Escolha se esta orientação ajudou você.")
    else:
        ArticleFeedback.objects.update_or_create(article=article, user=request.user, defaults={"helpful": choice == "yes"})
        messages.success(request, "Obrigado! Sua avaliação ajuda a melhorar as orientações.")
    return redirect("article_detail", pk=pk)


@login_required
def article_manage(request):
    if not is_support(request.user):
        raise PermissionDenied
    articles = filter_articles(visible_articles(request.user), request.GET)
    state = request.GET.get("state")
    if state in ("published", "draft"):
        articles = articles.filter(published=state == "published")
    articles = articles.annotate(
        helpful_count=Count("feedback", filter=Q(feedback__helpful=True)),
        unhelpful_count=Count("feedback", filter=Q(feedback__helpful=False)),
    ).order_by("-featured", "title", "pk")
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "desk/article_manage.html", {
        "page_obj": Paginator(articles, 15).get_page(request.GET.get("page")),
        "filter_query": params.urlencode(),
    })


@login_required
def article_edit(request, pk=None):
    if not is_support(request.user):
        raise PermissionDenied
    article = get_object_or_404(KnowledgeArticle, pk=pk) if pk else None
    form = ArticleForm(request.POST if request.method == "POST" else None, instance=article)
    if request.method == "POST" and form.is_valid():
        article = form.save(commit=False)
        if not article.pk:
            article.author = request.user
        article.updated_by = request.user
        article.save()
        messages.success(request, "Artigo publicado." if article.published else "Rascunho salvo. Somente a equipe de TI consegue visualizá-lo.")
        return redirect("article_detail", pk=article.pk)
    return render(request, "desk/article_form.html", {"form": form, "article": article})
