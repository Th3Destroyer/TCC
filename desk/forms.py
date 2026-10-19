from django import forms
from django.db.models import Q

from .models import Category, Department, KnowledgeArticle, Ticket
from .permissions import support_users
from .services import TRANSITIONS


class TicketForm(forms.ModelForm):
    source_article = forms.ModelChoiceField(
        queryset=KnowledgeArticle.objects.filter(published=True),
        required=False, widget=forms.HiddenInput, label="Orientação consultada",
    )

    class Meta:
        model = Ticket
        fields = ["title", "kind", "category", "department", "priority", "equipment", "description", "source_article"]
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
        if self.instance.kind == Ticket.Kind.QUESTION:
            self.fields["resolution"].label = "Resposta / orientação"
            self.fields["resolution"].widget.attrs["placeholder"] = "Explique a resposta e os passos que o usuário deve seguir."


class CommentForm(forms.Form):
    body = forms.CharField(label="Mensagem", max_length=10000, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Compartilhe uma atualização sobre este chamado…"}))
    internal = forms.BooleanField(label="Nota interna (visível apenas para a equipe de TI)", required=False)

    def __init__(self, *args, support=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not support:
            del self.fields["internal"]


class ArticleForm(forms.ModelForm):
    class Meta:
        model = KnowledgeArticle
        fields = ["title", "summary", "category", "body", "featured", "published"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Ex.: como configurar a impressora da unidade?"}),
            "summary": forms.Textarea(attrs={"rows": 2, "placeholder": "Explique em uma frase o que a pessoa aprenderá."}),
            "body": forms.Textarea(attrs={"rows": 14, "placeholder": "Escreva as orientações em passos claros, uma etapa por linha."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(Q(active=True) | Q(pk=self.instance.category_id))
        self.fields["category"].empty_label = "Orientações gerais"
        self.fields["body"].help_text = "Use texto simples. Não inclua senhas, dados pessoais ou informações reservadas nos artigos."
        self.fields["published"].help_text = "Quando desmarcado, somente a equipe de TI consegue visualizar o artigo."
