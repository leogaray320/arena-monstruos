from django.contrib import admin

from .models import Batalla, Entrenador, Item, Monstruo


@admin.register(Entrenador)
class EntrenadorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "creado")
    search_fields = ("nombre", "email")


@admin.register(Monstruo)
class MonstruoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tipo",
        "nivel",
        "hp",
        "ataque",
        "defensa",
        "entrenador",
    )
    list_filter = ("tipo", "entrenador")
    search_fields = ("nombre",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("nombre", "bonus_ataque", "bonus_defensa")
    search_fields = ("nombre",)


@admin.register(Batalla)
class BatallaAdmin(admin.ModelAdmin):
    list_display = ("monstruo_a", "monstruo_b", "ganador", "turnos", "fecha")
    list_filter = ("fecha",)
