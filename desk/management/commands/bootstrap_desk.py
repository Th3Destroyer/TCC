from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from desk.help_content import INITIAL_ARTICLES
from desk.models import Category, Department, KnowledgeArticle
from desk.permissions import MANAGER_GROUP, TECHNICIAN_GROUP


class Command(BaseCommand):
    help = "Cria perfis, categorias, unidades e orientações iniciais, sem sobrescrever cadastros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        Group.objects.get_or_create(name=TECHNICIAN_GROUP)
        managers, _ = Group.objects.get_or_create(name=MANAGER_GROUP)
        managers.permissions.add(*Permission.objects.filter(content_type__app_label="desk", codename__in=[
            "view_ticket", "view_ticketevent", "view_comment", "view_category", "add_category", "change_category",
            "view_department", "add_department", "change_department",
            "view_knowledgearticle",
        ]))
        for name in ["Hardware", "Software", "Conectividade", "Impressoras", "Telefonia", "Criação de usuários"]:
            Category.objects.get_or_create(name=name)
        for name in ["Administração", "Educação", "Saúde", "Finanças", "Obras", "Assistência Social"]:
            Department.objects.get_or_create(name=name)
        for content in INITIAL_ARTICLES:
            KnowledgeArticle.objects.get_or_create(bootstrap_key=content["key"], defaults={
                "title": content["title"], "summary": content["summary"], "body": content["body"],
                "category": Category.objects.get(name=content["category"]) if content["category"] else None,
                "featured": content["featured"], "published": True,
            })
        self.stdout.write(self.style.SUCCESS("Perfis, 6 categorias, unidades e orientações iniciais disponíveis. Nenhuma conta ou senha criada."))
