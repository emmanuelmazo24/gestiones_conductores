"""
Vistas para importar desde una Google Sheet pública.
Flujo: formulario → previsualización → confirmación → guardado.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone

from .public_sheets_service import extraer_desde_hoja_publica, fetch_csv, fetch_api_key
from .public_sheets_forms import HojaPublicaForm, ConfirmarImportForm
from .models import Conductor, SincronizacionLog
from . import excel_service


# ── PASO 1: FORMULARIO DE URL ─────────────────────────────────────────────────

def hoja_publica(request):
    """
    Muestra el formulario para ingresar la URL de la hoja pública.
    Al enviar, extrae los datos y redirige a la previsualización.
    """
    form = HojaPublicaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        url    = form.cleaned_data['url_hoja']
        apikey = form.cleaned_data.get('api_key', '')
        rango  = form.cleaned_data.get('rango') or 'A:Z'

        result = extraer_desde_hoja_publica(url, api_key=apikey, rango=rango)

        if not result['ok']:
            messages.error(request, f'❌ Error al extraer datos: {result["error"]}')
            return render(request, 'conductores/hoja_publica.html', {'form': form})

        # Guardar resultado en sesión para el paso de confirmación
        request.session['preview_result'] = {
            'sheet_id':   result['sheet_id'],
            'gid':        result['gid'],
            'api_key':    apikey,
            'rango':      rango,
            'metodo':     result['metodo'],
            'headers':    result['headers'],
            'conductores': result['conductores'],
            'total':      result['total'],
        }
        return redirect('conductores:hoja_publica_preview')

    google_auth = False
    try:
        from . import google_service
        google_auth = google_service.is_authenticated()
    except Exception:
        pass

    return render(request, 'conductores/hoja_publica.html', {
        'form': form,
        'google_auth': google_auth,
    })


# ── PASO 2: PREVISUALIZACIÓN ──────────────────────────────────────────────────

def hoja_publica_preview(request):
    """
    Muestra los datos extraídos antes de confirmar la importación.
    """
    preview = request.session.get('preview_result')
    if not preview:
        messages.warning(request, 'No hay datos para previsualizar. Ingresá la URL primero.')
        return redirect('conductores:hoja_publica')

    confirm_form = ConfirmarImportForm(initial={
        'sheet_id': preview['sheet_id'],
        'gid':      preview['gid'],
        'api_key':  preview['api_key'],
        'rango':    preview['rango'],
        'metodo':   preview['metodo'],
    })

    # Detectar columnas mapeadas vs sin mapear
    from .public_sheets_service import COLUMN_MAP, _map_headers
    mapping = _map_headers(preview['headers'])
    mapped_fields   = set(mapping.keys())
    unmapped_headers = [
        h for i, h in enumerate(preview['headers'])
        if i not in mapping.values()
    ]

    google_auth = False
    try:
        from . import google_service
        google_auth = google_service.is_authenticated()
    except Exception:
        pass

    return render(request, 'conductores/hoja_publica_preview.html', {
        'preview':          preview,
        'confirm_form':     confirm_form,
        'mapped_fields':    mapped_fields,
        'unmapped_headers': unmapped_headers,
        'muestra':          preview['conductores'][:5],  # primeras 5 filas
        'google_auth':      google_auth,
    })


# ── PASO 3: CONFIRMAR E IMPORTAR ─────────────────────────────────────────────

def hoja_publica_importar(request):
    """
    Re-extrae los datos frescos y los guarda en la BD local.
    """
    if request.method != 'POST':
        return redirect('conductores:hoja_publica')

    form = ConfirmarImportForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Formulario inválido.')
        return redirect('conductores:hoja_publica_preview')

    sheet_id   = form.cleaned_data['sheet_id']
    gid        = form.cleaned_data['gid']
    api_key    = form.cleaned_data.get('api_key', '')
    rango      = form.cleaned_data.get('rango', 'A:Z')
    metodo     = form.cleaned_data['metodo']
    modo_merge = form.cleaned_data['modo_merge']

    # Re-extraer datos frescos
    if metodo == 'api_key' and api_key:
        result = fetch_api_key(sheet_id, api_key, rango)
    else:
        result = fetch_csv(sheet_id, gid)

    if not result['ok']:
        messages.error(request, f'❌ Error al re-extraer: {result["error"]}')
        return redirect('conductores:hoja_publica')

    conductores_data = result['conductores']
    creados = actualizados = omitidos = 0

    if modo_merge == 'replace':
        Conductor.objects.all().delete()

    for data in conductores_data:
        # Quitar campos auxiliares que no son del modelo
        raw = data.pop('raw_data', {})
        nombre   = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()

        if not nombre:
            omitidos += 1
            continue

        if modo_merge == 'skip':
            obj, created = Conductor.objects.get_or_create(
                nombre=nombre, apellido=apellido,
                defaults=data,
            )
            if created:
                creados += 1
            else:
                omitidos += 1

        elif modo_merge in ('update', 'replace'):
            obj, created = Conductor.objects.update_or_create(
                nombre=nombre, apellido=apellido,
                defaults=data,
            )
            if created:
                creados += 1
            else:
                actualizados += 1

    # Log
    SincronizacionLog.objects.create(
        tipo='import',
        registros=creados + actualizados,
        archivo=f'sheets:{sheet_id}',
        exitoso=True,
        mensaje=f'Hoja pública ({metodo}) — creados:{creados} actualizados:{actualizados} omitidos:{omitidos}',
    )

    # Limpiar sesión
    request.session.pop('preview_result', None)

    msg = f'✔ Importación completada — {creados} nuevos'
    if actualizados:
        msg += f', {actualizados} actualizados'
    if omitidos:
        msg += f', {omitidos} omitidos'
    messages.success(request, msg)
    return redirect('conductores:lista')


# ── EXPORTAR PREVISUALIZACIÓN A EXCEL ─────────────────────────────────────────

def hoja_publica_exportar_preview(request):
    """
    Descarga los datos de la previsualización como Excel sin guardar en BD.
    """
    preview = request.session.get('preview_result')
    if not preview:
        messages.warning(request, 'No hay datos para exportar.')
        return redirect('conductores:hoja_publica')

    # Construir objetos Conductor en memoria (sin guardar)
    from .models import Conductor as ConductorModel
    objs = []
    for d in preview['conductores']:
        d_clean = {k: v for k, v in d.items() if k != 'raw_data'}
        if d_clean.get('nombre'):
            objs.append(ConductorModel(**d_clean))

    buffer   = excel_service.exportar_excel(objs)
    filename = f'preview_hoja_publica_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
