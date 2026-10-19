from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from desk.models import ArticleFeedback, Category, Department, KnowledgeArticle, Ticket
from desk.permissions import TECHNICIAN_GROUP
from desk.services import claim_ticket, open_ticket, update_ticket


class HelpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Impressoras")
        cls.other_category = Category.objects.create(name="Software")
        cls.department = Department.objects.create(name="Saúde")
        cls.requester = User.objects.create_user("solicitante", password="Test-only-password!45")
        cls.other = User.objects.create_user("outro", password="Test-only-password!45")
        cls.technician = User.objects.create_user("tecnico", password="Test-only-password!45")
        cls.second_tech = User.objects.create_user("outro.tecnico")
        group = Group.objects.create(name=TECHNICIAN_GROUP)
        cls.technician.groups.add(group)
        cls.second_tech.groups.add(group)
        cls.article = KnowledgeArticle.objects.create(
            title="Como resolver falha de impressão?", summary="Confira papel e conexão.",
            body="Verifique a mensagem no painel.\nSe precisar, envie uma dúvida.",
            category=cls.category, published=True, featured=True, author=cls.technician,
        )
        cls.draft = KnowledgeArticle.objects.create(
            title="Procedimento reservado de impressão", summary="Rascunho não publicado.",
            body="Conteúdo ainda em revisão.", category=cls.category, published=False,
        )
        cls.general = KnowledgeArticle.objects.create(
            title="Como escolher a prioridade?", summary="Considere o impacto.",
            body="Orientação geral de atendimento.", published=True,
        )

    def ticket(self, actor=None, **kwargs):
        data = {
            "title": "Dúvida de impressão", "description": "Como configurar frente e verso?",
            "kind": "question", "category": self.category, "department": self.department,
            "priority": "low", "source_article": self.article,
        }
        data.update(kwargs)
        return open_ticket(actor or self.requester, data)

    def article_data(self, **changes):
        data = {"title": "Configurar uma impressora", "summary": "Etapas para pedir ajuda.", "body": "Informe o patrimônio à TI.", "category": self.category.pk}
        data.update(changes)
        return data

    def test_authentication_required_for_help_and_question(self):
        for url in ["/ajuda/", "/ajuda/perguntar/", reverse("article_detail", args=[self.article.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(APIClient().get("/api/articles/").status_code, 403)

    def test_help_lists_only_published_articles_and_filters_content(self):
        self.client.force_login(self.requester)
        page = self.client.get("/ajuda/")
        self.assertContains(page, self.article.title)
        self.assertNotContains(page, self.draft.title)
        found = self.client.get("/ajuda/?q=painel")
        self.assertEqual(found.context["page_obj"].paginator.count, 1)
        self.assertEqual(found.context["page_obj"][0], self.article)
        self.assertEqual(self.client.get(f"/ajuda/?category={self.category.pk}").context["page_obj"].paginator.count, 1)
        general = self.client.get("/ajuda/?category=general")
        self.assertEqual(general.context["page_obj"][0], self.general)
        self.assertContains(self.client.get("/ajuda/?q=nada-encontrado"), "Nenhuma orientação encontrada")

    def test_drafts_are_private_even_if_requester_knows_id(self):
        self.client.force_login(self.requester)
        url = reverse("article_detail", args=[self.draft.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.technician)
        self.assertContains(self.client.get(url), "visível somente para a equipe de TI")
        self.assertNotContains(self.client.get("/ajuda/"), self.draft.title)

    def test_requester_and_staff_without_role_cannot_manage_articles(self):
        self.requester.is_staff = True
        self.requester.save()
        self.client.force_login(self.requester)
        for url in ["/ajuda/gerenciar/", "/ajuda/artigos/novo/", reverse("article_edit", args=[self.article.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, self.article_data()).status_code, 403)

    def test_support_creates_draft_publishes_and_preserves_authorship(self):
        self.client.force_login(self.technician)
        result = self.client.post("/ajuda/artigos/novo/", self.article_data())
        article = KnowledgeArticle.objects.get(title="Configurar uma impressora")
        self.assertRedirects(result, reverse("article_detail", args=[article.pk]))
        self.assertFalse(article.published)
        self.assertEqual(article.author, self.technician)
        self.assertEqual(article.updated_by, self.technician)
        self.client.force_login(self.second_tech)
        result = self.client.post(reverse("article_edit", args=[article.pk]), self.article_data(published="on", featured="on"))
        self.assertEqual(result.status_code, 302)
        article.refresh_from_db()
        self.assertTrue(article.published)
        self.assertEqual(article.author, self.technician)
        self.assertEqual(article.updated_by, self.second_tech)
        self.client.force_login(self.requester)
        self.assertContains(self.client.get(reverse("article_detail", args=[article.pk])), "Informe o patrimônio")

    def test_unpublishing_preserves_article_and_hides_it(self):
        ticket = self.ticket()
        self.client.force_login(self.technician)
        self.client.post(reverse("article_edit", args=[self.article.pk]), self.article_data(title=self.article.title))
        self.article.refresh_from_db()
        self.assertFalse(self.article.published)
        self.client.force_login(self.requester)
        self.assertEqual(self.client.get(reverse("article_detail", args=[self.article.pk])).status_code, 404)
        detail = self.client.get(reverse("ticket_detail", args=[ticket.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, self.article.title)
        ticket.refresh_from_db()
        self.assertEqual(ticket.source_article_id, self.article.pk)

    def test_article_content_is_escaped(self):
        KnowledgeArticle.objects.filter(pk=self.article.pk).update(body="<script>alert('x')</script>")
        self.client.force_login(self.requester)
        page = self.client.get(reverse("article_detail", args=[self.article.pk]))
        self.assertContains(page, "&lt;script&gt;")
        self.assertNotContains(page, "<script>alert")

    def test_feedback_is_one_per_user_and_can_be_changed(self):
        self.client.force_login(self.requester)
        url = reverse("article_feedback", args=[self.article.pk])
        for choice in ["yes", "yes", "no"]:
            self.assertEqual(self.client.post(url, {"helpful": choice}).status_code, 302)
        self.assertEqual(ArticleFeedback.objects.count(), 1)
        self.assertFalse(ArticleFeedback.objects.get().helpful)
        self.client.force_login(self.other)
        self.client.post(url, {"helpful": "yes"})
        self.assertEqual(ArticleFeedback.objects.count(), 2)
        self.client.force_login(self.technician)
        article = self.client.get("/ajuda/gerenciar/").context["page_obj"][0]
        self.assertEqual(article.pk, self.article.pk)
        self.assertEqual(article.helpful_count, 1)
        self.assertEqual(article.unhelpful_count, 1)

    def test_feedback_requires_post_csrf_and_published_article(self):
        self.client.force_login(self.requester)
        url = reverse("article_feedback", args=[self.article.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url, {"helpful": "unknown"})
        self.assertFalse(ArticleFeedback.objects.exists())
        self.assertEqual(self.client.post(reverse("article_feedback", args=[self.draft.pk]), {"helpful": "yes"}).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.requester)
        self.assertEqual(client.post(url, {"helpful": "yes"}).status_code, 403)

    def test_question_form_uses_article_context_and_forces_question_type(self):
        self.client.force_login(self.requester)
        url = f"/ajuda/perguntar/?article={self.article.pk}"
        form = self.client.get(url).context["form"]
        self.assertEqual(form.initial["source_article"], self.article)
        self.assertEqual(form.initial["category"], self.category.pk)
        result = self.client.post(url, {
            "title": "Ainda tenho uma dúvida", "description": "Como escolho a impressora?", "kind": "incident",
            "category": self.category.pk, "department": self.department.pk, "priority": "low", "source_article": self.article.pk,
        })
        self.assertEqual(result.status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.kind, "question")
        self.assertEqual(ticket.requester, self.requester)
        self.assertEqual(ticket.source_article_id, self.article.pk)
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), self.article.title)

    def test_question_cannot_reference_unpublished_article(self):
        self.client.force_login(self.requester)
        result = self.client.post("/ajuda/perguntar/", {
            "title": "Pergunta", "description": "Como proceder?", "priority": "low", "department": self.department.pk,
            "category": self.category.pk, "source_article": self.draft.pk,
        })
        self.assertEqual(result.status_code, 200)
        self.assertIn("source_article", result.context["form"].errors)
        self.assertFalse(Ticket.objects.exists())
        with self.assertRaises(ValidationError):
            self.ticket(source_article=self.draft)

    def test_question_filters_counts_and_export_respect_scope(self):
        question = self.ticket()
        self.ticket(kind="incident", title="Falha técnica")
        self.ticket(actor=self.other, title="Dúvida de outra pessoa")
        self.client.force_login(self.requester)
        help_page = self.client.get("/ajuda/")
        self.assertEqual(help_page.context["open_questions"], 1)
        page = self.client.get("/chamados/?kind=question")
        self.assertEqual(page.context["page_obj"].paginator.count, 1)
        self.assertEqual(page.context["queue_counts"]["questions"], 1)
        self.assertContains(page, question.title)
        self.assertNotContains(page, "Falha técnica")
        self.client.force_login(self.technician)
        export = self.client.get("/chamados/exportar/?kind=question").content.decode("utf-8-sig")
        self.assertIn("Dúvida de outra pessoa", export)
        self.assertNotIn("Falha técnica", export)

    def test_support_claims_ticket_with_history_but_no_response_timestamp(self):
        ticket = self.ticket()
        claimed = claim_ticket(self.technician, ticket, ticket.version)
        self.assertEqual(claimed.assigned_to, self.technician)
        self.assertEqual(claimed.status, "triage")
        self.assertIsNone(claimed.first_response_at)
        self.assertEqual(claimed.events.count(), 2)
        self.assertEqual(claimed.events.first().actor, self.technician)
        with self.assertRaises(ValidationError):
            claim_ticket(self.second_tech, claimed, claimed.version)
        claimed.refresh_from_db()
        self.assertEqual(claimed.assigned_to, self.technician)

    def test_claim_requires_support_current_version_and_active_ticket(self):
        ticket = self.ticket()
        with self.assertRaises(PermissionDenied):
            claim_ticket(self.requester, ticket, ticket.version)
        with self.assertRaises(ValidationError):
            claim_ticket(self.technician, ticket, 0)
        ticket = claim_ticket(self.technician, ticket, ticket.version)
        ticket = update_ticket(self.technician, ticket, {"status": "in_progress"}, ticket.version)
        ticket = update_ticket(self.technician, ticket, {"status": "resolved", "resolution": "Orientação fornecida."}, ticket.version)
        with self.assertRaises(ValidationError):
            claim_ticket(self.technician, ticket, ticket.version)

    def test_web_claim_and_unassigned_queue(self):
        ticket = self.ticket()
        self.client.force_login(self.requester)
        url = reverse("ticket_action", args=[ticket.pk, "claim"])
        self.assertEqual(self.client.post(url, {"version": ticket.version}).status_code, 403)
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get("/chamados/?unassigned=1").context["page_obj"].paginator.count, 1)
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "Assumir chamado")
        self.assertEqual(self.client.post(url, {"version": ticket.version}).status_code, 302)
        self.assertEqual(self.client.get("/chamados/?unassigned=1").context["page_obj"].paginator.count, 0)
        self.assertEqual(self.client.get("/chamados/?mine=1").context["page_obj"].paginator.count, 1)

    def test_article_management_pages_and_pagination(self):
        self.client.force_login(self.technician)
        for url in ["/ajuda/gerenciar/", "/ajuda/artigos/novo/", reverse("article_edit", args=[self.article.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        for index in range(10):
            KnowledgeArticle.objects.create(title=f"Artigo {index}", summary="Resumo", body="Orientação", published=True)
        self.client.force_login(self.requester)
        page = self.client.get("/ajuda/?page=2")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["page_obj"].number, 2)
        self.assertContains(page, "Anterior")

    def test_api_exposes_only_published_articles_and_is_read_only(self):
        api = APIClient()
        api.force_authenticate(self.requester)
        self.assertEqual(api.get("/api/articles/").data["count"], 2)
        self.assertEqual(api.get("/api/articles/?q=painel").data["count"], 1)
        self.assertEqual(api.get(f"/api/articles/{self.draft.pk}/").status_code, 404)
        self.assertEqual(api.get(f"/api/articles/{self.article.pk}/").data["body"], self.article.body)
        self.assertEqual(api.post("/api/articles/", self.article_data()).status_code, 405)

    def test_api_question_creation_filter_and_claim(self):
        api = APIClient()
        api.force_authenticate(self.requester)
        data = {"title": "Pergunta pela API", "description": "Como configurar?", "kind": "question", "category": self.category.pk, "department": self.department.pk, "priority": "low", "source_article": self.article.pk}
        result = api.post("/api/tickets/", data)
        self.assertEqual(result.status_code, 201, result.data)
        ticket_id = result.data["id"]
        self.assertEqual(result.data["source_article"], self.article.pk)
        self.ticket(kind="incident")
        self.assertEqual(api.get("/api/tickets/?kind=question").data["count"], 1)
        claim_url = f"/api/tickets/{ticket_id}/claim/"
        self.assertEqual(api.post(claim_url, {"version": 1}).status_code, 403)
        api.force_authenticate(self.technician)
        self.assertEqual(api.post(claim_url, {"version": "1"}).status_code, 400)
        result = api.post(claim_url, {"version": 1})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["assigned_to"], self.technician.pk)
        self.assertEqual(result.data["status"], "triage")

    def test_api_rejects_draft_source_on_creation(self):
        api = APIClient()
        api.force_authenticate(self.requester)
        result = api.post("/api/tickets/", {"title": "Dúvida", "description": "Teste", "kind": "question", "category": self.category.pk, "department": self.department.pk, "source_article": self.draft.pk})
        self.assertEqual(result.status_code, 400)
        self.assertFalse(Ticket.objects.exists())


class HelpBootstrapTests(TestCase):
    def test_initial_articles_are_repeatable_and_preserve_edits(self):
        call_command("bootstrap_desk", stdout=StringIO())
        self.assertEqual(KnowledgeArticle.objects.count(), 10)
        article = KnowledgeArticle.objects.get(bootstrap_key="senha-esquecida")
        article.body = "Orientação revisada pela prefeitura."
        article.published = False
        article.save()
        call_command("bootstrap_desk", stdout=StringIO())
        self.assertEqual(KnowledgeArticle.objects.count(), 10)
        article.refresh_from_db()
        self.assertEqual(article.body, "Orientação revisada pela prefeitura.")
        self.assertFalse(article.published)
        self.assertFalse(User.objects.exists())
