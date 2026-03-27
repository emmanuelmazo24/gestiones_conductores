from django import forms


class HojaPublicaForm(forms.Form):
    url_hoja = forms.CharField(
        label='URL o ID de la hoja de Google Sheets',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'https://docs.google.com/spreadsheets/d/1BxiMV.../edit',
        }),
        help_text='La hoja debe ser pública (cualquiera con el enlace puede verla).',
    )
    api_key = forms.CharField(
        label='API Key de Google (opcional)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'AIzaSy... — solo necesaria si el método CSV falla',
        }),
        help_text='Si dejás este campo vacío se intenta el método CSV directo, '
                  'que funciona sin ninguna credencial.',
    )
    rango = forms.CharField(
        label='Rango de celdas (solo para API Key)',
        required=False,
        initial='A:Z',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'A:Z  o  Hoja1!A1:L100',
        }),
    )

    def clean_url_hoja(self):
        from .public_sheets_service import extraer_id_desde_url
        val = self.cleaned_data['url_hoja'].strip()
        try:
            extraer_id_desde_url(val)
        except ValueError as e:
            raise forms.ValidationError(str(e))
        return val


class ConfirmarImportForm(forms.Form):
    """Formulario oculto para confirmar la importación tras la previsualización."""
    sheet_id   = forms.CharField(widget=forms.HiddenInput)
    gid        = forms.CharField(widget=forms.HiddenInput, initial='0')
    api_key    = forms.CharField(widget=forms.HiddenInput, required=False)
    rango      = forms.CharField(widget=forms.HiddenInput, initial='A:Z')
    metodo     = forms.CharField(widget=forms.HiddenInput)   # 'csv' | 'api_key'
    modo_merge = forms.ChoiceField(
        label='¿Qué hacer con registros duplicados?',
        choices=[
            ('skip',    'Ignorar duplicados (solo agregar nuevos)'),
            ('update',  'Actualizar registros existentes'),
            ('replace', 'Borrar todo y reemplazar'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='skip',
    )
