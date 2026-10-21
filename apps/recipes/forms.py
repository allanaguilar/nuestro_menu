from django import forms

from apps.recipes.models import Recipe
from apps.recipes.selectors import find_duplicates
from apps.recipes.services import parse_recipe_import_text


class RecipeForm(forms.ModelForm):
    confirm_duplicate = forms.BooleanField(
        required=False,
        label="Guardar aunque exista una receta con un nombre parecido",
    )

    class Meta:
        model = Recipe
        fields = ("name", "category", "prep_time_minutes", "notes")
        labels = {
            "name": "Nombre",
            "category": "Categoría",
            "prep_time_minutes": "Tiempo de preparación (minutos)",
            "notes": "Notas",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, household=None, **kwargs):
        self.household = household
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} field-input".strip()

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        if name and self.household:
            duplicates = find_duplicates(
                self.household,
                name,
                exclude_id=self.instance.pk if self.instance.pk else None,
            )
            if duplicates.exists() and not cleaned.get("confirm_duplicate"):
                names = ", ".join(duplicates.values_list("name", flat=True)[:5])
                raise forms.ValidationError(
                    "Ya hay una receta con un nombre equivalente "
                    f"({names}). Confirma si quieres guardarla igualmente."
                )
        return cleaned

    def save(self, commit=True):
        recipe = super().save(commit=False)
        recipe.household = self.household
        if commit:
            recipe.save()
        return recipe


class RecipeImportForm(forms.Form):
    text = forms.CharField(
        label="Lista de recetas",
        widget=forms.Textarea(
            attrs={
                "rows": 16,
                "class": "field-input import-text",
                "placeholder": "Patatas a la riojana\nPasta con carne | pasta\nSalmón con verduras | pescado | Airfryer",
            }
        ),
        help_text=(
            "Una receta por línea. Opcional: Nombre | categoría | notas. "
            "Si no pones categoría, se infiere por el nombre."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        css = self.fields["text"].widget.attrs.get("class", "")
        self.fields["text"].widget.attrs["class"] = f"{css} field-input".strip()

    def clean_text(self):
        text = self.cleaned_data["text"]
        if not parse_recipe_import_text(text):
            raise forms.ValidationError("No hay recetas que importar. Escribe una por línea.")
        return text
