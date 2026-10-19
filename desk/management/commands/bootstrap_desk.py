from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from desk.models import Category, Department
from desk.permissions import MANAGER_GROUP, TECHNICIAN_GROUP


class Command(BaseCommand):
    help = "Cria os perfis, categorias e unidades iniciais, sem sobrescrever cadastros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        Group.objects.get_or_create(name=TECHNICIAN_GROUP)
        managers, _ = Group.objects.get_or_create(name=MANAGER_GROUP)
        managers.permissions.add(*Permission.objects.filter(content_type__app_label="desk", codename__in=[
            "view_ticket", "view_ticketevent", "view_comment", "view_category", "add_category", "change_category",
            "view_department", "add_department", "change_department",
        ]))
        for name in ["Hardware", "Software", "Conectividade", "Impressoras", "Telefonia", "Criação de usuários"]:
            Category.objects.get_or_create(name=name)
        for name in ["Administração", "Educação", "Saúde", "Finanças", "Obras", "Assistência Social"]:
            Department.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Perfis, 6 categorias e unidades iniciais disponíveis. Nenhuma conta ou senha criada."))
