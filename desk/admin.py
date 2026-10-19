from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Category, Comment, Department, Profile, Ticket, TicketEvent

admin.site.site_header = "Service Desk · Administração"
admin.site.site_title = "Service Desk Municipal"
admin.site.index_title = "Gestão de usuários e cadastros"


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


class DeskUserAdmin(UserAdmin):
    inlines = [ProfileInline]


admin.site.unregister(User)
admin.site.register(User, DeskUserAdmin)


@admin.register(Category, Department)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ["name", "active"]
    list_filter = ["active"]
    search_fields = ["name"]


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(ReadOnlyAdmin):
    list_display = ["id", "title", "department", "category", "priority", "status", "assigned_to"]
    list_filter = ["status", "priority", "category", "department"]
    search_fields = ["title", "equipment", "requester__username"]


@admin.register(TicketEvent)
class TicketEventAdmin(ReadOnlyAdmin):
    list_display = ["ticket", "actor", "created_at"]


@admin.register(Comment)
class CommentAdmin(ReadOnlyAdmin):
    list_display = ["ticket", "author", "internal", "created_at"]
