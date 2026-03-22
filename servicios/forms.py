from django import forms
from .models import Servicio, CatalogoServicios


class ServicioForm(forms.ModelForm):
    categoria = forms.ChoiceField(
        required=False,
        label="Categoría",
        widget=forms.Select(attrs={'class': 'select select-bordered select-primary w-full'}),
    )
    subcategoria_codigo = forms.ChoiceField(
        required=True,
        label="Subcategoría",
        widget=forms.Select(attrs={'class': 'select select-bordered select-primary w-full'}),
    )
    descripcion = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full h-32',
            'placeholder': 'Describe brevemente qué servicio se realizará...',
        }),
        label="Descripción",
    )

    class Meta:
        model = Servicio
        fields = ['subcategoria_codigo', 'titulo', 'descripcion', 'publico']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input input-bordered input-primary w-full focus:input-primary',
                'placeholder': 'Ingrese el nombre del servicio',
            }),
            'publico': forms.CheckboxInput(attrs={
                'class': 'toggle toggle-primary',
            }),
        }
        labels = {
            'titulo': 'Nombre del Servicio',
            'publico': 'Público',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        catalogo = CatalogoServicios.get_activo()
        datos = catalogo.datos if catalogo else []

        cat_choices = [('', '— Selecciona una categoría —')]
        sub_choices = [('', '— Selecciona una subcategoría —')]
        for cat in datos:
            cat_choices.append((cat['nombre'], cat['nombre']))
            for sub in cat.get('subcategorias', []):
                sub_choices.append((sub['codigo'], f"{sub['codigo']} — {sub['nombre']}"))

        self.fields['categoria'].choices = cat_choices
        self.fields['subcategoria_codigo'].choices = sub_choices

        # Pre-select category when editing an existing instance
        if self.instance.pk and self.instance.categoria_nombre:
            self.fields['categoria'].initial = self.instance.categoria_nombre
