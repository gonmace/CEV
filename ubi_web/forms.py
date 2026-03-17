from django import forms
from decimal import Decimal, InvalidOperation
from .models import Ubicacion


class UbicacionForm(forms.ModelForm):
    coordenadas = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Ej: -17.768244, -63.145478',
        }),
        label='Coordenadas (lat, lon)',
    )

    class Meta:
        model = Ubicacion
        fields = ['nombre', 'descripcion', 'ciudad']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Ingrese el nombre de la ubicación'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Ingrese una descripción de la ubicación (opcional)'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Ej: Santa Cruz de la Sierra',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and instance.latitud is not None and instance.longitud is not None:
            self.fields['coordenadas'].initial = f"{instance.latitud}, {instance.longitud}"

    def clean_coordenadas(self):
        value = self.cleaned_data.get('coordenadas', '').strip()
        if not value:
            return None
        # Remove all spaces around the comma
        parts = [p.strip() for p in value.split(',')]
        if len(parts) != 2:
            raise forms.ValidationError('Formato inválido. Use: latitud, longitud (Ej: -17.768244, -63.145478)')
        try:
            lat = Decimal(parts[0])
            lon = Decimal(parts[1])
        except InvalidOperation:
            raise forms.ValidationError('Las coordenadas deben ser números válidos.')
        if not (-90 <= lat <= 90):
            raise forms.ValidationError('La latitud debe estar entre -90 y 90.')
        if not (-180 <= lon <= 180):
            raise forms.ValidationError('La longitud debe estar entre -180 y 180.')
        return (lat, lon)

    def save(self, commit=True):
        instance = super().save(commit=False)
        coords = self.cleaned_data.get('coordenadas')
        if coords:
            instance.latitud, instance.longitud = coords
        else:
            instance.latitud = None
            instance.longitud = None
        if commit:
            instance.save()
        return instance


class UbicacionContenidoForm(forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'class': 'hidden',
            }),
        }
        labels = {
            'contenido': 'Contenido (Markdown)',
        }
