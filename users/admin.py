from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Utilisateur, Role, Permission, MembreProjet


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'id')
    search_fields = ('code', 'description')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description', 'id')
    search_fields = ('nom', 'description')
    filter_horizontal = ('permissions',)


@admin.register(Utilisateur)
class UtilisateurAdmin(BaseUserAdmin):
    list_display = ('email', 'nom', 'statut', 'dateCreation', 'derniereConnexion', 'is_staff', 'is_superuser')
    list_filter = ('statut', 'is_staff', 'is_superuser')
    search_fields = ('email', 'nom')
    ordering = ('-dateCreation',)
    filter_horizontal = ('roles', 'groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom', 'statut', 'derniereConnexion')}),
        ('Rôles et Permissions', {'fields': ('roles', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'password', 'statut'),
        }),
    )


@admin.register(MembreProjet)
class MembreProjetAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'dateAffectation', 'actif', 'id')
    list_filter = ('actif', 'dateAffectation')
    search_fields = ('utilisateur__nom', 'utilisateur__email')
