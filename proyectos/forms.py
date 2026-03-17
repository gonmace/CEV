from django import forms
from .models import Proyecto, Especificacion


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'solicitante', 'ubicacion', 'descripcion', 'publico']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'input input-bordered input-primary w-full focus:input-primary',
                'placeholder': 'Ingrese el nombre del proyecto'
            }),
            'solicitante': forms.TextInput(attrs={
                'class': 'input input-bordered input-primary w-full focus:input-primary',
                'placeholder': 'Ingrese el nombre del solicitante'
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'input input-bordered input-primary w-full focus:input-primary',
                'placeholder': 'Ingrese la ubicación del proyecto'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered textarea-primary w-full focus:textarea-primary',
                'rows': 4,
                'placeholder': 'Ingrese una descripción del proyecto (opcional)'
            }),
            'publico': forms.CheckboxInput(attrs={
                'class': 'toggle toggle-primary'
            }),
        }
        labels = {
            'nombre': 'Nombre de Proyecto',
            'solicitante': 'Solicitante',
            'ubicacion': 'Ubicación',
            'descripcion': 'Descripción',
            'publico': 'Público',
        }


class EspecificacionForm(forms.ModelForm):
    class Meta:
        model = Especificacion
        fields = ['titulo', 'contenido']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Ingrese el título de la especificación'
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-64 font-mono',
                'placeholder': 'Contenido en formato Markdown'
            }),
        }
        labels = {
            'titulo': 'Título',
            'contenido': 'Contenido (Markdown)',
        }

