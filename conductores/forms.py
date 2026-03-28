from django import forms
from .models import Conductor, GRUPOS


class ConductorForm(forms.ModelForm):
    fecha_recepcion = forms.DateField(
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
        label='Fecha de recepción',
    )

    class Meta:
        model  = Conductor
        fields = [
            'nombre', 'apellido', 'cedula', 'edad', 'direccion',
            'nombre_padres', 'numero_contacto_adulto',
            'comunidad', 'dificultades', 'fecha_recepcion', 'grupo',
            'asistencia_dia_1', 'asistencia_dia_2', 'asistencia_dia_3',
        ]
        widgets = {
            'nombre':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido':               forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'cedula':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cedula'}),
            'edad':                   forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 120}),
            'direccion':              forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'nombre_padres':          forms.TextInput(attrs={'class': 'form-control'}),
            'numero_contacto_adulto': forms.TextInput(attrs={'class': 'form-control', 'type': 'tel'}),
            'comunidad':              forms.TextInput(attrs={'class': 'form-control'}),
            'dificultades':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                        'placeholder': 'Describir dificultades o necesidades especiales...'}),
            'grupo':                  forms.Select(attrs={'class': 'form-select'}),
            'asistencia_dia_1':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'asistencia_dia_2':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'asistencia_dia_3':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FiltroForm(forms.Form):
    q     = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Buscar por nombre, comunidad...'}))
    grupo = forms.ChoiceField(required=False, choices=[('', 'Todos los grupos')] + GRUPOS,
                              widget=forms.Select(attrs={'class': 'form-select'}))


class ImportarExcelForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo Excel (.xlsx)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}),
    )
