from django import forms

from .models import Entrenador, Monstruo


class MonstruoForm(forms.ModelForm):
    """Formulario para crear y editar monstruos e inspeccionar sus archivos."""

    MAX_FOTO_BYTES = 2 * 1024 * 1024

    class Meta:
        model = Monstruo
        fields = [
            "nombre",
            "tipo",
            "emoji",
            "foto",
            "hp",
            "ataque",
            "defensa",
            "entrenador",
            "items",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: Pyroclasto"}),
            "emoji": forms.TextInput(attrs={"maxlength": 8}),
            "items": forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            "hp": "Entre 50 y 250",
            "ataque": "Entre 10 y 120",
            "defensa": "Entre 10 y 120",
        }

    def clean_nombre(self):
        """Ejemplo de validacion de un campo puntual."""
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 letras.")
        return nombre

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if foto:
            if foto.size > self.MAX_FOTO_BYTES:
                raise forms.ValidationError("La foto no puede superar los 2 MB.")
            extension_valida = foto.name.lower().endswith((".jpg", ".jpeg", ".png"))
            formato_valido = getattr(getattr(foto, "image", None), "format", None)
            if not extension_valida or formato_valido not in {"JPEG", "PNG"}:
                raise forms.ValidationError("La foto debe estar en formato JPG o PNG.")
        return foto


class EntrenadorForm(forms.ModelForm):
    class Meta:
        model = Entrenador
        fields = ["nombre", "email"]


class ArenaForm(forms.Form):
    monstruo_a = forms.ModelChoiceField(
        queryset=Monstruo.objects.select_related("entrenador").all(),
        label="Primer monstruo",
        empty_label="Elige un monstruo",
    )
    monstruo_b = forms.ModelChoiceField(
        queryset=Monstruo.objects.select_related("entrenador").all(),
        label="Segundo monstruo",
        empty_label="Elige un monstruo",
    )

    def clean(self):
        cleaned_data = super().clean()
        monstruo_a = cleaned_data.get("monstruo_a")
        monstruo_b = cleaned_data.get("monstruo_b")
        if monstruo_a and monstruo_b and monstruo_a.pk == monstruo_b.pk:
            raise forms.ValidationError("Elige dos monstruos distintos para pelear.")
        return cleaned_data
