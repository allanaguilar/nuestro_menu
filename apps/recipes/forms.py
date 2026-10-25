from django import forms

from apps.recipes.models import Recipe
from apps.recipes.services import parse_recipe_import_text


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ("name", "category", "prep_time_minutes", "ingredients", "steps", "is_meal")
        labels = {
            "name": "Nombre",
            "category": "Categoría",
            "prep_time_minutes": "Tiempo (minutos)",
            "ingredients": "Ingredientes",
            "steps": "Pasos",
            "is_meal": "Sale como comida de un día",
        }
        widgets = {
            "ingredients": forms.Textarea(attrs={"class": "recipe-text", "rows": 8}),
            "steps": forms.Textarea(attrs={"class": "recipe-text", "rows": 8}),
        }

    def __init__(self, *args, household=None, **kwargs):
        self.household = household
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} field-input".strip()

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
