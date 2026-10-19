from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from desk.metrics import ticket_metrics
from desk.models import Category, Comment, Department, Ticket, TicketEvent
from desk.permissions import MANAGER_GROUP, TECHNICIAN_GROUP, is_support, visible_tickets
from desk.services import add_comment, open_ticket, requester_action, update_ticket


class DeskTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="Saúde")
        cls.category = Category.objects.create(name="Hardware")
        cls.requester = User.objects.create_user("ana", password="Test-only-password!45", first_name="Ana")
        cls.other = User.objects.create_user("bruno", password="Test-only-password!45")
        cls.technician = User.objects.create_user("tecnico", password="Test-only-password!45", first_name="Carlos")
        cls.manager = User.objects.create_user("gestor", password="Test-only-password!45")
        cls.technician.groups.add(Group.objects.create(name=TECHNICIAN_GROUP))
        cls.manager.groups.add(Group.objects.create(name=MANAGER_GROUP))

    def ticket(self, actor=None, **kwargs):
        data = {
            "title": "Computador da recepção não liga", "description": "Sem sinal de energia desde as 8h.",
            "kind": "incident", "category": self.category, "department": self.department,
            "equipment": "PAT-001", "priority": "high",
        }
        data.update(kwargs)
        return open_ticket(actor or self.requester, data)

    def update(self, ticket, **kwargs):
        ticket.refresh_from_db()
        return update_ticket(self.technician, ticket, kwargs, ticket.version)

    def resolved_ticket(self):
        ticket = self.ticket()
        ticket = self.update(ticket, assigned_to=self.technician, status="in_progress")
        return self.update(ticket, status="resolved", resolution="Fonte substituída e equipamento testado.")


class WorkflowTests(DeskTestCase):
    def test_opening_records_owner_reference_and_audit(self):
        ticket = self.ticket()
        self.assertEqual(ticket.requester, self.requester)
        self.assertEqual(ticket.status, "open")
        self.assertIsNone(ticket.assigned_to)
        self.assertIn(f"{ticket.pk:05d}", ticket.reference)
        self.assertEqual(ticket.events.get().actor, self.requester)

    def test_complete_lifecycle_and_solution_confirmation(self):
        ticket = self.ticket()
        ticket = self.update(ticket, status="triage", assigned_to=self.technician)
        self.assertIsNone(ticket.first_response_at)
        ticket = self.update(ticket, status="in_progress")
        self.assertIsNotNone(ticket.first_response_at)
        ticket = self.update(ticket, status="waiting")
        ticket = self.update(ticket, status="resolved", resolution="Fonte substituída.")
        self.assertIsNotNone(ticket.resolved_at)
        self.assertTrue(ticket.comments.filter(body__contains="Fonte substituída.").exists())
        ticket = requester_action(self.requester, ticket, "close", ticket.version)
        self.assertEqual(ticket.status, "closed")
        self.assertIsNotNone(ticket.closed_at)
        self.assertEqual(ticket.events.count(), 6)

    def test_cannot_skip_from_open_to_resolved_or_closed(self):
        ticket = self.ticket()
        for status in ["resolved", "closed"]:
            with self.subTest(status=status), self.assertRaises(ValidationError):
                self.update(ticket, status=status, assigned_to=self.technician, resolution="Teste")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.events.count(), 1)

    def test_responsible_technician_is_required(self):
        with self.assertRaises(ValidationError):
            self.update(self.ticket(), status="in_progress")

    def test_cannot_assign_requester_or_inactive_technician(self):
        ticket = self.ticket()
        with self.assertRaises(ValidationError):
            self.update(ticket, assigned_to=self.requester)
        self.technician.is_active = False
        self.technician.save()
        with self.assertRaises(PermissionDenied):
            self.update(ticket, assigned_to=self.technician)

    def test_solution_is_required_and_invalid_change_rolls_back(self):
        ticket = self.update(self.ticket(), status="in_progress", assigned_to=self.technician)
        with self.assertRaises(ValidationError):
            self.update(ticket, status="resolved", resolution="   ")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "in_progress")
        self.assertIsNone(ticket.resolved_at)

    def test_requester_cannot_change_classification(self):
        ticket = self.ticket()
        with self.assertRaises(PermissionDenied):
            update_ticket(self.requester, ticket, {"priority": "critical"}, ticket.version)

    def test_unrelated_requester_cannot_comment_or_close(self):
        ticket = self.resolved_ticket()
        with self.assertRaises(PermissionDenied):
            add_comment(self.other, ticket, "Não é meu chamado")
        with self.assertRaises(PermissionDenied):
            requester_action(self.other, ticket, "close", ticket.version)

    def test_requester_cannot_create_internal_note(self):
        with self.assertRaises(PermissionDenied):
            add_comment(self.requester, self.ticket(), "Segredo", internal=True)

    def test_internal_notes_and_requester_comments_do_not_count_as_response(self):
        ticket = self.ticket()
        add_comment(self.requester, ticket, "Ainda não funciona")
        add_comment(self.technician, ticket, "Análise interna", internal=True)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.first_response_at)
        add_comment(self.technician, ticket, "Vamos verificar o equipamento.")
        ticket.refresh_from_db()
        first_response = ticket.first_response_at
        self.assertIsNotNone(first_response)
        add_comment(self.technician, ticket, "Teste concluído.")
        ticket.refresh_from_db()
        self.assertEqual(ticket.first_response_at, first_response)

    def test_reopening_preserves_previous_solution_in_conversation(self):
        ticket = self.resolved_ticket()
        first_response = ticket.first_response_at
        ticket = requester_action(self.requester, ticket, "close", ticket.version)
        ticket = requester_action(self.requester, ticket, "reopen", ticket.version)
        self.assertEqual(ticket.status, "triage")
        self.assertEqual(ticket.resolution, "")
        self.assertIsNone(ticket.resolved_at)
        self.assertIsNone(ticket.closed_at)
        self.assertEqual(ticket.first_response_at, first_response)
        self.assertTrue(ticket.comments.filter(body__contains="Fonte substituída").exists())

    def test_edited_solution_also_remains_in_history(self):
        ticket = self.resolved_ticket()
        ticket = self.update(ticket, resolution="Fonte e cabo substituídos.")
        requester_action(self.requester, ticket, "reopen", ticket.version)
        self.assertTrue(ticket.comments.filter(body__contains="Fonte e cabo substituídos.").exists())

    def test_cannot_comment_on_closed_ticket_or_close_open_ticket(self):
        ticket = self.resolved_ticket()
        ticket = requester_action(self.requester, ticket, "close", ticket.version)
        with self.assertRaises(ValidationError):
            add_comment(self.requester, ticket, "Mensagem depois do encerramento")
        opened = self.ticket()
        with self.assertRaises(ValidationError):
            requester_action(self.requester, opened, "close", opened.version)

    def test_stale_form_cannot_overwrite_newer_change(self):
        ticket = self.ticket()
        old_version = ticket.version
        self.update(ticket, status="triage")
        with self.assertRaises(ValidationError):
            update_ticket(self.technician, ticket, {"priority": "critical"}, old_version)
        ticket.refresh_from_db()
        self.assertEqual(ticket.priority, "high")
        self.assertEqual(ticket.status, "triage")

    def test_metrics_use_real_response_and_solution_intervals(self):
        start = timezone.now() - timedelta(hours=6)
        ticket = self.ticket()
        Ticket.objects.filter(pk=ticket.pk).update(created_at=start, first_response_at=start + timedelta(hours=1), resolved_at=start + timedelta(hours=4), status="resolved")
        self.ticket(equipment="OTHER")
        metrics = ticket_metrics(visible_tickets(self.requester))
        self.assertEqual(metrics["response_hours"], 1.0)
        self.assertEqual(metrics["resolution_hours"], 4.0)
        self.assertEqual(metrics["response_samples"], 1)
        self.assertEqual(metrics["active"], 1)
        self.assertEqual(metrics["resolved"], 1)
        self.assertEqual(sum(day["count"] for day in metrics["days"]), 2)

    def test_profile_and_roles(self):
        self.assertIsNotNone(self.requester.desk_profile)
        self.assertFalse(is_support(self.requester))
        self.assertTrue(is_support(self.technician))
        self.assertTrue(is_support(self.manager))


class WebTests(DeskTestCase):
    def test_login_required_and_no_public_registration(self):
        self.assertRedirects(self.client.get("/"), "/entrar/?next=/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/entrar/").status_code, 200)

    def test_login_logout_and_password_change(self):
        response = self.client.post("/entrar/", {"username": "ana", "password": "Test-only-password!45"})
        self.assertRedirects(response, "/")
        response = self.client.post("/senha/", {"old_password": "Test-only-password!45", "new_password1": "New-test-password!67", "new_password2": "New-test-password!67"})
        self.assertRedirects(response, "/senha/alterada/")
        self.assertEqual(self.client.get("/sair/").status_code, 405)
        self.assertRedirects(self.client.post("/sair/"), "/entrar/")

    def test_requester_only_sees_own_tickets_in_dashboard_list_and_detail(self):
        own = self.ticket()
        foreign = self.ticket(actor=self.other, title="Incidente restrito de outra pessoa")
        self.client.force_login(self.requester)
        self.assertContains(self.client.get("/"), own.title)
        self.assertNotContains(self.client.get("/"), foreign.title)
        self.assertNotContains(self.client.get("/chamados/"), foreign.title)
        self.assertEqual(self.client.get(reverse("ticket_detail", args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.get("/indicadores/").status_code, 403)
        self.assertEqual(self.client.get("/chamados/exportar/").status_code, 403)

    def test_web_opening_and_comment(self):
        self.client.force_login(self.requester)
        response = self.client.post("/chamados/novo/", {
            "title": "Erro na impressora", "description": "Papel não é reconhecido.", "kind": "incident",
            "category": self.category.pk, "department": self.department.pk, "priority": "medium", "equipment": "IMP-01",
        })
        ticket = Ticket.objects.get()
        self.assertRedirects(response, reverse("ticket_detail", args=[ticket.pk]))
        response = self.client.post(reverse("ticket_detail", args=[ticket.pk]), {"action": "comment", "body": "O erro persiste."})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ticket.comments.get().body, "O erro persiste.")

    def test_internal_note_not_rendered_for_requester(self):
        ticket = self.ticket()
        add_comment(self.technician, ticket, "Detalhe técnico reservado", internal=True)
        self.client.force_login(self.requester)
        self.assertNotContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "Detalhe técnico reservado")
        self.client.force_login(self.technician)
        self.assertContains(self.client.get(reverse("ticket_detail", args=[ticket.pk])), "Detalhe técnico reservado")

    def test_support_pages_render_and_filters_work(self):
        ticket = self.ticket()
        self.ticket(title="Falha no telefone", priority="low")
        self.client.force_login(self.technician)
        for url in ["/", "/chamados/", "/chamados/novo/", "/indicadores/", "/senha/", reverse("ticket_detail", args=[ticket.pk])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        filtered = self.client.get("/chamados/?priority=high")
        self.assertContains(filtered, ticket.title)
        self.assertNotContains(filtered, "Falha no telefone")
        self.assertContains(self.client.get(f"/chamados/?q={ticket.reference}"), ticket.title)

    def test_web_update_and_validation(self):
        ticket = self.ticket()
        self.client.force_login(self.technician)
        data = {"action": "update", "version": ticket.version, "kind": ticket.kind, "category": ticket.category_id, "department": ticket.department_id, "priority": ticket.priority, "status": "in_progress", "assigned_to": "", "resolution": ""}
        response = self.client.post(reverse("ticket_detail", args=[ticket.pk]), data)
        self.assertContains(response, "Defina um responsável")
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "open")
        data["assigned_to"] = self.technician.pk
        response = self.client.post(reverse("ticket_detail", args=[ticket.pk]), data)
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "in_progress")
        self.assertIsNotNone(ticket.first_response_at)

    def test_csrf_protection_on_login_and_ticket_creation(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/entrar/", {"username": "ana", "password": "Test-only-password!45"}).status_code, 403)
        client.force_login(self.requester)
        self.assertEqual(client.post("/chamados/novo/", {}).status_code, 403)

    def test_csv_export_neutralizes_spreadsheet_formulas(self):
        self.ticket(title="=HYPERLINK(1)")
        self.client.force_login(self.technician)
        response = self.client.get("/chamados/exportar/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("'=HYPERLINK(1)", response.content.decode("utf-8-sig"))

    def test_html_is_escaped(self):
        ticket = self.ticket(description="<script>alert('x')</script>")
        self.client.force_login(self.requester)
        page = self.client.get(reverse("ticket_detail", args=[ticket.pk]))
        self.assertContains(page, "&lt;script&gt;")
        self.assertNotContains(page, "<script>alert")


class ApiTests(DeskTestCase):
    def setUp(self):
        self.api = APIClient()

    def test_anonymous_access_denied(self):
        self.assertEqual(self.api.get("/api/tickets/").status_code, 403)
        self.assertEqual(self.api.get("/api/metrics/").status_code, 403)

    def test_api_open_and_owner_enforced(self):
        self.api.force_authenticate(self.requester)
        response = self.api.post("/api/tickets/", {"title": "Conta bloqueada", "description": "Não consigo acessar o sistema.", "kind": "request", "category": self.category.pk, "department": self.department.pk, "priority": "medium"})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["requester"], self.requester.pk)
        self.assertEqual(response.data["status"], "open")
        self.assertEqual(response.data["version"], 1)

    def test_create_cannot_inject_assignment_or_owner(self):
        self.api.force_authenticate(self.requester)
        response = self.api.post("/api/tickets/", {"title": "Teste", "description": "Descrição", "category": self.category.pk, "department": self.department.pk, "assigned_to": self.technician.pk, "requester": self.other.pk})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Ticket.objects.exists())

    def test_scoped_api_list_detail_comments_and_history(self):
        own = self.ticket()
        foreign = self.ticket(actor=self.other)
        self.api.force_authenticate(self.requester)
        data = self.api.get("/api/tickets/").data
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], own.pk)
        for suffix in ["", "comments/", "history/"]:
            self.assertEqual(self.api.get(f"/api/tickets/{foreign.pk}/{suffix}").status_code, 404)

    def test_requester_patch_delete_and_global_metrics_denied(self):
        ticket = self.ticket()
        self.api.force_authenticate(self.requester)
        self.assertEqual(self.api.patch(f"/api/tickets/{ticket.pk}/", {"priority": "critical", "version": ticket.version}).status_code, 403)
        self.assertEqual(self.api.delete(f"/api/tickets/{ticket.pk}/").status_code, 405)
        self.assertEqual(self.api.get("/api/metrics/").status_code, 403)

    def test_support_patch_requires_version_and_respects_workflow(self):
        ticket = self.ticket()
        self.api.force_authenticate(self.technician)
        path = f"/api/tickets/{ticket.pk}/"
        self.assertEqual(self.api.patch(path, {"status": "triage"}).status_code, 400)
        response = self.api.patch(path, {"status": "in_progress", "assigned_to": self.technician.pk, "version": ticket.version})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "in_progress")
        self.assertEqual(self.api.patch(path, {"status": "closed", "version": response.data["version"]}).status_code, 400)
        self.assertEqual(self.api.patch(path, {"priority": "low", "version": 1}).status_code, 400)

    def test_comments_filter_internal_notes(self):
        ticket = self.ticket()
        self.api.force_authenticate(self.technician)
        url = f"/api/tickets/{ticket.pk}/comments/"
        self.assertEqual(self.api.post(url, {"body": "Reservado", "internal": True}).status_code, 201)
        self.assertEqual(self.api.post(url, {"body": "Resposta pública"}).status_code, 201)
        self.api.force_authenticate(self.requester)
        response = self.api.get(url)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["body"], "Resposta pública")
        self.assertEqual(self.api.post(url, {"body": "Tentativa", "internal": True}).status_code, 403)

    def test_confirmation_and_reopening_endpoints(self):
        ticket = self.resolved_ticket()
        self.api.force_authenticate(self.requester)
        response = self.api.post(f"/api/tickets/{ticket.pk}/close/", {"version": ticket.version})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "closed")
        response = self.api.post(f"/api/tickets/{ticket.pk}/reopen/", {"version": response.data["version"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "triage")

    def test_active_catalogs_and_metrics(self):
        Category.objects.create(name="Desativada", active=False)
        self.api.force_authenticate(self.technician)
        self.assertEqual(self.api.get("/api/categories/").data["count"], 1)
        self.assertEqual(self.api.get("/api/departments/").data["count"], 1)
        self.ticket()
        self.assertEqual(self.api.get("/api/metrics/").data["total"], 1)


class SetupTests(TestCase):
    def test_bootstrap_is_idempotent_and_preserves_existing_settings(self):
        call_command("bootstrap_desk", stdout=StringIO())
        Category.objects.filter(name="Hardware").update(active=False)
        call_command("bootstrap_desk", stdout=StringIO())
        self.assertEqual(Category.objects.count(), 6)
        self.assertEqual(Department.objects.count(), 6)
        self.assertEqual(Group.objects.count(), 2)
        self.assertFalse(Category.objects.get(name="Hardware").active)
        self.assertFalse(User.objects.exists())

    def test_audit_cannot_be_modified_in_admin(self):
        from desk.admin import TicketEventAdmin
        from django.contrib.admin.sites import AdminSite
        instance = TicketEventAdmin(TicketEvent, AdminSite())
        self.assertFalse(instance.has_add_permission(None))
        self.assertFalse(instance.has_change_permission(None))
        self.assertFalse(instance.has_delete_permission(None))
