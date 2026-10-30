"""
Tests de la Arena de Monstruos.

Ejecutar:  python manage.py test juego -v 2
"""
import io
import os
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from .combate import pelear
from .models import Batalla, Entrenador, Item, Monstruo


def crear_png(ancho=2, alto=2):
    imagen = Image.new("RGB", (ancho, alto), color="red")
    contenido = io.BytesIO()
    imagen.save(contenido, format="PNG")
    return contenido.getvalue()


class BaseDatos(TestCase):
    def setUp(self):
        self.entrenador = Entrenador.objects.create(nombre="Ash", email="ash@inacap.cl")
        self.fuego = Monstruo.objects.create(
            nombre="Pyroclasto",
            tipo="fuego",
            hp=120,
            ataque=70,
            defensa=40,
            entrenador=self.entrenador,
        )
        self.planta = Monstruo.objects.create(
            nombre="Raizul",
            tipo="planta",
            hp=140,
            ataque=50,
            defensa=60,
            entrenador=self.entrenador,
        )


class ModeloTests(BaseDatos):
    def test_str_incluye_el_nombre(self):
        self.assertIn("Pyroclasto", str(self.fuego))

    def test_costo_stats(self):
        # 70 + 40 + 120/2 = 170
        self.assertEqual(self.fuego.costo_stats(), 170)

    def test_ventaja_de_tipo(self):
        self.assertTrue(self.fuego.es_fuerte_contra(self.planta))
        self.assertFalse(self.planta.es_fuerte_contra(self.fuego))


class CombateTests(BaseDatos):
    def test_combate_es_reproducible_con_semilla(self):
        uno = pelear(self.fuego, self.planta, semilla=42)
        otro = pelear(self.fuego, self.planta, semilla=42)
        self.assertEqual(uno["ganador"], otro["ganador"])
        self.assertEqual(uno["turnos"], otro["turnos"])


class CrudTests(BaseDatos):
    def test_listado_entrenadores_muestra_datos_y_sus_monstruos(self):
        respuesta = self.client.get(reverse("juego:entrenadores"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Entrenadores")
        self.assertContains(respuesta, "Ash")
        self.assertContains(respuesta, "ash@inacap.cl")
        self.assertContains(respuesta, "Pyroclasto")
        self.assertContains(
            respuesta,
            f'href="{reverse("juego:entrenador_nuevo")}">+ Registrar entrenador</a>',
        )

    def test_listado_entrenadores_pagina_de_ocho(self):
        for numero in range(8):
            Entrenador.objects.create(
                nombre=f"Entrenador {numero}",
                email=f"entrenador{numero}@example.com",
            )

        respuesta = self.client.get(reverse("juego:entrenadores"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total"], 9)
        self.assertEqual(respuesta.context["pagina"].paginator.per_page, 8)
        self.assertContains(respuesta, "page=2")

    def test_pestana_entrenadores_muestra_formulario_de_registro(self):
        respuesta = self.client.get(reverse("juego:lista"))
        self.assertContains(
            respuesta,
            f'href="{reverse("juego:entrenadores")}">Entrenadores</a>',
        )

        respuesta_entrenador = self.client.get(reverse("juego:entrenador_nuevo"))
        self.assertEqual(respuesta_entrenador.status_code, 200)
        self.assertContains(respuesta_entrenador, "Registra un entrenador nuevo")
        self.assertContains(respuesta_entrenador, "Registrar entrenador")

    def test_se_pueden_registrar_varios_entrenadores_seguidos(self):
        for nombre, email in (
            ("Misty", "misty@example.com"),
            ("Brock", "brock@example.com"),
        ):
            respuesta = self.client.post(
                reverse("juego:entrenador_nuevo"),
                {"nombre": nombre, "email": email},
            )
            self.assertRedirects(
                respuesta, reverse("juego:entrenador_nuevo")
            )

        self.assertTrue(
            Entrenador.objects.filter(email="misty@example.com").exists()
        )
        self.assertTrue(
            Entrenador.objects.filter(email="brock@example.com").exists()
        )

    def test_listado_muestra_monstruos(self):
        respuesta = self.client.get(reverse("juego:lista"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Pyroclasto")

    def test_crear_monstruo(self):
        datos = {
            "nombre": "Chispazo",
            "tipo": "electrico",
            "emoji": "⚡",
            "hp": 100,
            "ataque": 60,
            "defensa": 40,
            "entrenador": self.entrenador.pk,
        }
        respuesta = self.client.post(reverse("juego:crear"), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Monstruo.objects.filter(nombre="Chispazo").exists())

    def test_nombre_muy_corto_es_rechazado(self):
        datos = {
            "nombre": "AB",
            "tipo": "agua",
            "emoji": "\U0001f30a",
            "hp": 100,
            "ataque": 50,
            "defensa": 50,
            "entrenador": self.entrenador.pk,
        }
        self.client.post(reverse("juego:crear"), datos)
        self.assertFalse(Monstruo.objects.filter(nombre="AB").exists())

    def test_presupuesto_excedido_se_rechaza_en_el_formulario(self):
        datos = {
            "nombre": "Sobrecargado",
            "tipo": "agua",
            "emoji": "🌊",
            "hp": 250,
            "ataque": 120,
            "defensa": 120,
            "entrenador": self.entrenador.pk,
        }
        respuesta = self.client.post(reverse("juego:crear"), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "El monstruo gasta 365 puntos")
        self.assertFalse(Monstruo.objects.filter(nombre="Sobrecargado").exists())

    def test_clean_rechaza_monstruo_sobrecargado(self):
        self.fuego.hp = 250
        self.fuego.ataque = 120
        self.fuego.defensa = 120
        with self.assertRaises(ValidationError):
            self.fuego.full_clean()

    def test_busqueda_filtra_por_nombre_de_monstruo_o_entrenador(self):
        respuesta_nombre = self.client.get(reverse("juego:lista"), {"q": "Pyro"})
        self.assertContains(respuesta_nombre, "Pyroclasto")
        self.assertNotContains(respuesta_nombre, "Raizul")

        respuesta_entrenador = self.client.get(
            reverse("juego:lista"), {"q": "Ash"}
        )
        self.assertContains(respuesta_entrenador, "Pyroclasto")
        self.assertContains(respuesta_entrenador, "Raizul")

    def test_filtro_tipo_y_orden_ataque(self):
        respuesta = self.client.get(
            reverse("juego:lista"), {"tipo": "fuego", "orden": "ataque"}
        )
        self.assertContains(respuesta, "Pyroclasto")
        self.assertNotContains(respuesta, "Raizul")
        self.assertEqual(respuesta.context["orden"], "ataque")

    def test_paginacion_conserva_los_filtros(self):
        for numero in range(8):
            Monstruo.objects.create(
                nombre=f"Fuego {numero}",
                tipo="fuego",
                hp=100,
                ataque=40,
                defensa=40,
                entrenador=self.entrenador,
            )

        respuesta = self.client.get(
            reverse("juego:lista"),
            {"q": "Ash", "tipo": "fuego", "orden": "ataque", "page": 2},
        )
        self.assertEqual(respuesta.context["pagina"].number, 2)
        self.assertContains(
            respuesta,
            "?q=Ash&amp;tipo=fuego&amp;orden=ataque&amp;page=1",
        )


class OroTests(BaseDatos):
    def test_arena_guarda_la_pelea_y_muestra_el_resultado(self):
        respuesta = self.client.post(
            reverse("juego:arena"),
            {"monstruo_a": self.fuego.pk, "monstruo_b": self.planta.pk},
        )

        self.assertEqual(respuesta.status_code, 200)
        batalla = Batalla.objects.get()
        self.assertEqual(batalla.monstruo_a, self.fuego)
        self.assertEqual(batalla.monstruo_b, self.planta)
        self.assertGreater(batalla.turnos, 0)
        self.assertTrue(batalla.bitacora)
        self.assertContains(respuesta, f"Batalla #{batalla.pk} guardada")

    def test_arena_impide_que_un_monstruo_pelee_contra_si_mismo(self):
        respuesta = self.client.post(
            reverse("juego:arena"),
            {"monstruo_a": self.fuego.pk, "monstruo_b": self.fuego.pk},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Elige dos monstruos distintos")
        self.assertFalse(Batalla.objects.exists())

    def test_ranking_orm_y_sql_entregan_los_mismos_resultados_y_orden(self):
        sombra = Monstruo.objects.create(
            nombre="Sombra",
            tipo="sombra",
            hp=100,
            ataque=40,
            defensa=40,
            entrenador=self.entrenador,
        )
        novato = Monstruo.objects.create(
            nombre="Novato",
            tipo="agua",
            hp=100,
            ataque=40,
            defensa=40,
            entrenador=self.entrenador,
        )
        Batalla.objects.create(
            monstruo_a=self.fuego,
            monstruo_b=self.planta,
            ganador=self.fuego,
            turnos=2,
            bitacora="Victoria de Pyroclasto.",
        )
        Batalla.objects.create(
            monstruo_a=self.planta,
            monstruo_b=sombra,
            ganador=self.planta,
            turnos=3,
            bitacora="Victoria de Raizul.",
        )

        respuesta_orm = self.client.get(reverse("juego:ranking"))
        respuesta_sql = self.client.get(reverse("juego:ranking_sql"))
        self.assertEqual(respuesta_orm.status_code, 200)
        self.assertEqual(respuesta_sql.status_code, 200)

        filas_orm = [
            (m.nombre, m.entrenador.nombre, m.peleas, m.ganadas)
            for m in respuesta_orm.context["tabla"]
        ]
        filas_sql = [
            (f["nombre"], f["entrenador"], f["peleas"], f["ganadas"])
            for f in respuesta_sql.context["filas"]
        ]
        self.assertEqual(filas_sql, filas_orm)
        self.assertEqual(filas_orm[-1], ("Novato", "Ash", 0, 0))

    def test_historial_muestra_bitacora_y_pagina_batallas(self):
        for numero in range(9):
            Batalla.objects.create(
                monstruo_a=self.fuego,
                monstruo_b=self.planta,
                ganador=self.fuego,
                turnos=numero + 1,
                bitacora=f"Entrada {numero}",
            )

        respuesta = self.client.get(reverse("juego:historial"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["pagina"].paginator.count, 9)
        self.assertContains(respuesta, "Entrada 8")
        self.assertContains(respuesta, "page=2")


class DiamanteTests(BaseDatos):
    def test_items_suman_bonus_a_las_estadisticas_mostradas(self):
        item = Item.objects.create(
            nombre="Amuleto",
            bonus_ataque=10,
            bonus_defensa=5,
        )
        self.fuego.items.add(item)

        self.assertEqual(self.fuego.ataque, 70)
        self.assertEqual(self.fuego.ataque_total, 80)
        self.assertEqual(self.fuego.defensa_total, 45)

    def test_entrenar_sube_nivel_y_estadisticas(self):
        respuesta = self.client.post(
            reverse("juego:entrenar", args=[self.fuego.pk])
        )
        self.assertRedirects(
            respuesta, reverse("juego:detalle", args=[self.fuego.pk])
        )
        self.fuego.refresh_from_db()
        self.assertEqual(self.fuego.nivel, 2)
        self.assertEqual(self.fuego.ataque, 73)
        self.assertEqual(self.fuego.defensa, 43)
        self.assertEqual(self.fuego.hp, 125)

    def test_entrenar_bloquea_superar_presupuesto_sin_guardar_cambios(self):
        self.fuego.hp = 240
        self.fuego.ataque = 60
        self.fuego.defensa = 70
        self.fuego.save()

        respuesta = self.client.post(
            reverse("juego:entrenar", args=[self.fuego.pk]), follow=True
        )

        self.assertRedirects(
            respuesta, reverse("juego:detalle", args=[self.fuego.pk])
        )
        self.assertContains(respuesta, "No pudo entrenar")
        self.fuego.refresh_from_db()
        self.assertEqual(self.fuego.nivel, 1)
        self.assertEqual(self.fuego.hp, 240)
        self.assertEqual(self.fuego.ataque, 60)
        self.assertEqual(self.fuego.defensa, 70)

    def test_api_ranking_devuelve_json_con_estadisticas(self):
        respuesta = self.client.get(reverse("juego:api_ranking"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertEqual(
            respuesta.json()["ranking"][0],
            {
                "id": self.fuego.pk,
                "nombre": "Pyroclasto",
                "tipo": "fuego",
                "entrenador": "Ash",
                "nivel": 1,
                "peleas": 0,
                "ganadas": 0,
            },
        )

    def test_subir_foto_la_muestra_en_listado_y_detalle(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root
        ):
            imagen = SimpleUploadedFile(
                "criatura.png", crear_png(), content_type="image/png"
            )
            respuesta = self.client.post(
                reverse("juego:editar", args=[self.fuego.pk]),
                {
                    "nombre": self.fuego.nombre,
                    "tipo": self.fuego.tipo,
                    "emoji": self.fuego.emoji,
                    "hp": self.fuego.hp,
                    "ataque": self.fuego.ataque,
                    "defensa": self.fuego.defensa,
                    "entrenador": self.entrenador.pk,
                    "foto": imagen,
                },
            )
            self.assertRedirects(
                respuesta, reverse("juego:detalle", args=[self.fuego.pk])
            )
            self.fuego.refresh_from_db()
            self.assertTrue(os.path.isfile(self.fuego.foto.path))

            listado = self.client.get(reverse("juego:lista"))
            detalle = self.client.get(
                reverse("juego:detalle", args=[self.fuego.pk])
            )
            self.assertContains(listado, self.fuego.foto.url)
            self.assertContains(detalle, self.fuego.foto.url)

    def test_formulario_rechaza_archivo_que_no_es_una_imagen(self):
        archivo = SimpleUploadedFile(
            "falso.png", b"esto no es una imagen", content_type="image/png"
        )
        respuesta = self.client.post(
            reverse("juego:editar", args=[self.fuego.pk]),
            {
                "nombre": self.fuego.nombre,
                "tipo": self.fuego.tipo,
                "emoji": self.fuego.emoji,
                "hp": self.fuego.hp,
                "ataque": self.fuego.ataque,
                "defensa": self.fuego.defensa,
                "entrenador": self.entrenador.pk,
                "foto": archivo,
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].has_error("foto"))

    def test_formulario_rechaza_imagen_que_no_es_jpg_ni_png(self):
        imagen = Image.new("RGB", (2, 2), color="blue")
        contenido = io.BytesIO()
        imagen.save(contenido, format="GIF")
        archivo = SimpleUploadedFile(
            "criatura.gif", contenido.getvalue(), content_type="image/gif"
        )
        respuesta = self.client.post(
            reverse("juego:editar", args=[self.fuego.pk]),
            {
                "nombre": self.fuego.nombre,
                "tipo": self.fuego.tipo,
                "emoji": self.fuego.emoji,
                "hp": self.fuego.hp,
                "ataque": self.fuego.ataque,
                "defensa": self.fuego.defensa,
                "entrenador": self.entrenador.pk,
                "foto": archivo,
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].has_error("foto"))

    def test_formulario_rechaza_imagen_mayor_a_dos_megabytes(self):
        contenido = io.BytesIO()
        imagen = Image.frombytes("RGB", (1100, 1100), os.urandom(1100 * 1100 * 3))
        imagen.save(contenido, format="PNG", compress_level=0)
        self.assertGreater(len(contenido.getvalue()), 2 * 1024 * 1024)
        archivo = SimpleUploadedFile(
            "grande.png", contenido.getvalue(), content_type="image/png"
        )
        respuesta = self.client.post(
            reverse("juego:editar", args=[self.fuego.pk]),
            {
                "nombre": self.fuego.nombre,
                "tipo": self.fuego.tipo,
                "emoji": self.fuego.emoji,
                "hp": self.fuego.hp,
                "ataque": self.fuego.ataque,
                "defensa": self.fuego.defensa,
                "entrenador": self.entrenador.pk,
                "foto": archivo,
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "La foto no puede superar los 2 MB.")
