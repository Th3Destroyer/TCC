from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name):
    return format_html('<svg class="icon" aria-hidden="true"><use href="#icon-{}"></use></svg>', name)


@register.filter
def person(user):
    if not user:
        return "Não atribuído"
    return user.get_full_name() or user.username


@register.filter
def initials(user):
    name = person(user).split()
    return "".join(part[0] for part in name[:2]).upper()
