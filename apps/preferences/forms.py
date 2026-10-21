from django import forms

from apps.preferences.models import RecipePreference


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = RecipePreference
        fields = ("rating", "is_favorite", "is_avoided")
        labels = {
            "rating": "Puntuación",
            "is_favorite": "Favorita para mí",
            "is_avoided": "Evitar en el menú",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].required = False
        self.fields["rating"].widget = forms.Select(
            choices=[("", "Sin puntuar")] + [(i, str(i)) for i in range(1, 6)]
        )
        self.fields["rating"].widget.attrs["class"] = "field-input"
