from django import forms


class EspecificacionTecnicaForm(forms.Form):
    titulo = forms.CharField(
        label='Título',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Ingrese el título'
        })
    )
    
    descripcion = forms.CharField(
        label='Descripción',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 5,
            'placeholder': 'Ingrese la descripción'
        })
    )









