"""
Modelos de la Arena de Monstruos.

LO QUE YA ESTA HECHO:
    - Entrenador
    - Monstruo
    - Batalla

Cada vez que cambies este archivo:
    python manage.py makemigrations
    python manage.py migrate
"""
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

# Cada tipo es fuerte contra el tipo indicado: el dano se multiplica por 1.25.
VENTAJAS = {
    "fuego": "planta",
    "planta": "agua",
    "agua": "fuego",
    "electrico": "agua",
    "roca": "electrico",
    "sombra": "roca",
}

# Presupuesto de estadisticas: evita monstruos invencibles.
PRESUPUESTO_STATS = 250


class Entrenador(models.Model):
    nombre = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "entrenadores"

    def __str__(self):
        return self.nombre


class Item(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    bonus_ataque = models.PositiveIntegerField(default=0)
    bonus_defensa = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Monstruo(models.Model):
    TIPOS = [
        ("fuego", "Fuego"),
        ("agua", "Agua"),
        ("planta", "Planta"),
        ("electrico", "Electrico"),
        ("roca", "Roca"),
        ("sombra", "Sombra"),
    ]

    nombre = models.CharField(max_length=60, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    emoji = models.CharField(
        max_length=8, default="\U0001f47e", help_text="Un emoji que lo represente"
    )
    foto = models.ImageField(
        upload_to="monstruos/%Y/%m/", blank=True, null=True
    )
    hp = models.PositiveIntegerField(
        default=100, validators=[MinValueValidator(50), MaxValueValidator(250)]
    )
    ataque = models.PositiveIntegerField(
        default=50, validators=[MinValueValidator(10), MaxValueValidator(120)]
    )
    defensa = models.PositiveIntegerField(
        default=50, validators=[MinValueValidator(10), MaxValueValidator(120)]
    )
    nivel = models.PositiveIntegerField(default=1)
    entrenador = models.ForeignKey(
        Entrenador, on_delete=models.PROTECT, related_name="monstruos"
    )
    items = models.ManyToManyField(Item, blank=True, related_name="monstruos")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        indexes = [models.Index(fields=["tipo"], name="idx_monstruo_tipo")]

    def __str__(self):
        return f"{self.emoji} {self.nombre}"

    def get_absolute_url(self):
        return reverse("juego:detalle", args=[self.pk])

    # --- Reglas del juego ---------------------------------------------------
    def costo_stats(self):
        """Puntos gastados en estadisticas (el tope es PRESUPUESTO_STATS)."""
        return self.ataque + self.defensa + self.hp // 2

    def clean(self):
        super().clean()
        costo = self.costo_stats()
        if costo > PRESUPUESTO_STATS:
            raise ValidationError(
                f"El monstruo gasta {costo} puntos y el máximo es "
                f"{PRESUPUESTO_STATS}. Fórmula: ataque + defensa + hp/2."
            )

    @property
    def ataque_total(self):
        return self.ataque + sum(item.bonus_ataque for item in self.items.all())

    @property
    def defensa_total(self):
        return self.defensa + sum(item.bonus_defensa for item in self.items.all())

    @property
    def poder(self):
        return self.ataque_total + self.defensa_total + self.hp // 10 + self.nivel * 2

    def es_fuerte_contra(self, otro):
        return VENTAJAS.get(self.tipo) == otro.tipo

class Batalla(models.Model):
    monstruo_a = models.ForeignKey(
        Monstruo, on_delete=models.CASCADE, related_name="batallas_como_a"
    )
    monstruo_b = models.ForeignKey(
        Monstruo, on_delete=models.CASCADE, related_name="batallas_como_b"
    )
    ganador = models.ForeignKey(
        Monstruo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="batallas_ganadas",
    )
    turnos = models.PositiveIntegerField()
    bitacora = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]

    def __str__(self):
        return f"{self.monstruo_a.nombre} vs {self.monstruo_b.nombre}"

    def lineas_bitacora(self):
        return self.bitacora.splitlines()
