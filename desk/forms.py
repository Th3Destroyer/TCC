from django import forms
from django.db.models import Q

from .models import Category, Department, Ticket
from .permissions import support_users
from .services import TRANSITIONS


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "kind", "category", "department", "priority", "equipment", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex.: impressora não imprime na recepção"}),
            "description": forms.Textarea(attrs={"rows": 6, "placeholder": "Descreva o problema, quando começou e como afeta o trabalho da unidade."}),
            "equipment": forms.TextInput(attrs={"placeholder": "Ex.: patrimônio 001234 (opcional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(active=True)
        self.fields["department"].queryset = Department.objects.filter(active=True)
        self.fields["priority"].help_text = "Crítica: serviço essencial interrompido. Alta: várias pessoas afetadas. Média: impacto parcial. Baixa: dúvida ou solicitação sem urgência."


class TicketUpdateForm(forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput)

    class Meta:
        model = Ticket
        fields = ["kind", "category", "department", "priority", "assigned_to", "status", "resolution"]
        widgets = {"resolution": forms.Textarea(attrs={"rows": 4, "placeholder": "Registre o diagnóstico e a solução aplicada."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = support_users()
        self.fields["category"].queryset = Category.objects.filter(Q(active=True) | Q(pk=self.instance.category_id))
        self.fields["department"].queryset = Department.objects.filter(Q(active=True) | Q(pk=self.instance.department_id))
        available = TRANSITIONS.get(self.instance.status, set()) | {self.instance.status}
        self.fields["status"].choices = [(value, label) for value, label in Ticket.Status.choices if value in available]
        self.fields["version"].initial = self.instance.version


class CommentForm(forms.Form):
    body = forms.CharField(label="Mensagem", max_length=10000, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Compartilhe uma atualização sobre este chamado…"}))
    internal = forms.BooleanField(label="Nota interna (visível apenas para a equipe de TI)", required=False)

    def __init__(self, *args, support=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not support:
            del self.fields["internal"]
