from django.urls import path

from . import views

app_name = "juego"

urlpatterns = [
    # --- Ya funcionan ---
    path("", views.lista, name="lista"),
    path("monstruo/nuevo/", views.crear, name="crear"),
    path("entrenadores/", views.lista_entrenadores, name="entrenadores"),
    path("entrenador/nuevo/", views.entrenador_nuevo, name="entrenador_nuevo"),
    # --- BRONCE ---
    path("monstruo/<int:pk>/", views.detalle, name="detalle"),
    path("monstruo/<int:pk>/editar/", views.editar, name="editar"),
    path("monstruo/<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    # --- ORO ---
    path("arena/", views.arena, name="arena"),
    path("ranking/", views.ranking, name="ranking"),
    path("ranking/sql/", views.ranking_sql, name="ranking_sql"),
    path("historial/", views.historial, name="historial"),
    # --- DIAMANTE ---
    path("monstruo/<int:pk>/entrenar/", views.entrenar, name="entrenar"),
    path("api/ranking/", views.api_ranking, name="api_ranking"),
]
