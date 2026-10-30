"""
Vistas de la Arena de Monstruos.

YA ESTA HECHO:
    lista()   -> READ con busqueda, filtros, orden y paginacion
    crear()   -> el CREATE del CRUD
    detalle(), editar(), eliminar() -> CRUD BRONCE
    entrenador_nuevo()

TU TRABAJO (en este orden):
    No quedan vistas pendientes del enunciado.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .combate import pelear
from .forms import ArenaForm, EntrenadorForm, MonstruoForm
from .models import Batalla, Entrenador, Monstruo

POR_PAGINA = 8


# --------------------------------------------------------------------------- #
# READ
# --------------------------------------------------------------------------- #
def lista(request):
    """Muestra monstruos con búsqueda, filtros, orden y paginación."""
    monstruos = Monstruo.objects.select_related("entrenador").prefetch_related(
        "items"
    )
    busqueda = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    orden = request.GET.get("orden", "nombre")

    if busqueda:
        monstruos = monstruos.filter(
            Q(nombre__icontains=busqueda)
            | Q(entrenador__nombre__icontains=busqueda)
        )
    if tipo:
        monstruos = monstruos.filter(tipo=tipo)

    ordenamientos = {
        "nombre": "nombre",
        "ataque": "-ataque",
        "hp": "-hp",
    }
    orden = orden if orden in ordenamientos else "nombre"
    monstruos = monstruos.order_by(ordenamientos[orden], "nombre")

    total = monstruos.count()
    pagina = Paginator(monstruos, POR_PAGINA).get_page(request.GET.get("page"))
    filtros = request.GET.copy()
    filtros.pop("page", None)

    contexto = {
        "monstruos": pagina,
        "pagina": pagina,
        "filtros_query": filtros.urlencode(),
        "busqueda": busqueda,
        "tipo": tipo,
        "orden": orden,
        "tipos": Monstruo.TIPOS,
        "total": total,
    }
    return render(request, "juego/lista.html", contexto)


def lista_entrenadores(request):
    entrenadores = (
        Entrenador.objects.annotate(total_monstruos=Count("monstruos", distinct=True))
        .prefetch_related("monstruos")
        .order_by("nombre")
    )
    pagina = Paginator(entrenadores, POR_PAGINA).get_page(request.GET.get("page"))
    return render(
        request,
        "juego/entrenadores.html",
        {"pagina": pagina, "total": entrenadores.count()},
    )


def detalle(request, pk):
    monstruo = get_object_or_404(
        Monstruo.objects.prefetch_related("items"), pk=pk
    )
    return render(request, "juego/detalle.html", {"monstruo": monstruo})


# --------------------------------------------------------------------------- #
# CREATE / UPDATE / DELETE
# --------------------------------------------------------------------------- #
def crear(request):
    if not Entrenador.objects.exists():
        messages.warning(
            request, "Primero crea un entrenador: no hay a quien asignarle el monstruo."
        )
        return redirect("juego:entrenador_nuevo")

    form = MonstruoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        monstruo = form.save()
        messages.success(request, f"{monstruo.nombre} se unio a la arena.")
        return redirect("juego:lista")
    return render(
        request, "juego/formulario.html", {"form": form, "titulo": "Reclutar monstruo"}
    )


def editar(request, pk):
    monstruo = get_object_or_404(Monstruo, pk=pk)
    form = MonstruoForm(request.POST or None, request.FILES or None, instance=monstruo)
    if request.method == "POST" and form.is_valid():
        monstruo_actualizado = form.save()
        messages.success(request, f"{monstruo_actualizado.nombre} fue actualizado.")
        return redirect("juego:detalle", pk=monstruo_actualizado.pk)
    return render(
        request,
        "juego/formulario.html",
        {"form": form, "titulo": f"Editar {monstruo.nombre}"},
    )


def eliminar(request, pk):
    monstruo = get_object_or_404(Monstruo, pk=pk)
    if request.method == "POST":
        nombre = monstruo.nombre
        monstruo.delete()
        messages.success(request, f"{nombre} fue expulsado de la arena.")
        return redirect("juego:lista")
    return render(request, "juego/confirmar_eliminar.html", {"monstruo": monstruo})


def entrenador_nuevo(request):
    form = EntrenadorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrenador registrado.")
        return redirect("juego:entrenador_nuevo")
    return render(
        request,
        "juego/formulario.html",
        {"form": form, "titulo": "Registrar entrenador"},
    )


# --------------------------------------------------------------------------- #
# ORO: batallas y rankings
# --------------------------------------------------------------------------- #
def arena(request):
    form = ArenaForm(request.POST or None)
    resultado = None
    batalla = None
    if request.method == "POST" and form.is_valid():
        monstruo_a = form.cleaned_data["monstruo_a"]
        monstruo_b = form.cleaned_data["monstruo_b"]
        resultado = pelear(monstruo_a, monstruo_b)
        batalla = Batalla.objects.create(
            monstruo_a=monstruo_a,
            monstruo_b=monstruo_b,
            ganador=resultado["ganador"],
            turnos=resultado["turnos"],
            bitacora="\n".join(resultado["bitacora"]),
        )
        form = ArenaForm()
        messages.success(request, "La batalla terminó y quedó guardada en el historial.")
    return render(
        request,
        "juego/arena.html",
        {"form": form, "resultado": resultado, "batalla": batalla},
    )


def ranking(request):
    tabla = (
        Monstruo.objects.select_related("entrenador")
        .annotate(
            peleas=Count("batallas_como_a", distinct=True)
            + Count("batallas_como_b", distinct=True),
            ganadas=Count("batallas_ganadas", distinct=True),
        )
        .order_by("-ganadas", "-peleas", "nombre")
    )
    return render(request, "juego/ranking.html", {"tabla": tabla})


CONSULTA_RANKING_SQL = """
    SELECT  m.id, m.nombre, e.nombre AS entrenador,
            COUNT(DISTINCT b.id) AS peleas,
            COUNT(DISTINCT CASE WHEN b.ganador_id = m.id THEN b.id END) AS ganadas
    FROM        juego_monstruo   AS m
    INNER JOIN  juego_entrenador AS e ON e.id = m.entrenador_id
    LEFT JOIN   juego_batalla    AS b
            ON  b.monstruo_a_id = m.id OR b.monstruo_b_id = m.id
    GROUP BY    m.id, m.nombre, e.nombre
    ORDER BY    ganadas DESC, peleas DESC, m.nombre ASC
"""


def ranking_sql(request):
    with connection.cursor() as cursor:
        cursor.execute(CONSULTA_RANKING_SQL)
        columnas = [columna[0] for columna in cursor.description]
        filas = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    return render(
        request,
        "juego/ranking_sql.html",
        {"filas": filas, "consulta": CONSULTA_RANKING_SQL.strip()},
    )


def historial(request):
    batallas = Batalla.objects.select_related(
        "monstruo_a", "monstruo_b", "ganador"
    ).order_by("-fecha", "-pk")
    pagina = Paginator(batallas, POR_PAGINA).get_page(request.GET.get("page"))
    return render(request, "juego/historial.html", {"pagina": pagina})


@require_POST
def entrenar(request, pk):
    monstruo = get_object_or_404(Monstruo, pk=pk)
    monstruo.nivel += 1
    monstruo.ataque += 3
    monstruo.defensa += 3
    monstruo.hp += 5
    try:
        monstruo.full_clean()
    except ValidationError as error:
        messages.error(request, f"No pudo entrenar: {error.messages[0]}")
        return redirect("juego:detalle", pk=pk)

    monstruo.save()
    messages.success(request, f"{monstruo.nombre} subió al nivel {monstruo.nivel}.")
    return redirect("juego:detalle", pk=pk)


def api_ranking(request):
    monstruos = (
        Monstruo.objects.select_related("entrenador")
        .annotate(
            peleas=Count("batallas_como_a", distinct=True)
            + Count("batallas_como_b", distinct=True),
            ganadas=Count("batallas_ganadas", distinct=True),
        )
        .order_by("-ganadas", "-peleas", "nombre")
    )
    resultados = [
        {
            "id": monstruo.pk,
            "nombre": monstruo.nombre,
            "tipo": monstruo.tipo,
            "entrenador": monstruo.entrenador.nombre,
            "nivel": monstruo.nivel,
            "peleas": monstruo.peleas,
            "ganadas": monstruo.ganadas,
        }
        for monstruo in monstruos
    ]
    return JsonResponse({"ranking": resultados})
