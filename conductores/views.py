from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Conductor, SincronizacionLog, GRUPOS
from .forms import ConductorForm, FiltroForm, ImportarExcelForm
from . import google_service, excel_service


# ── LISTA Y BÚSQUEDA ──────────────────────────────────────────────────────────

def lista(request):
    form = FiltroForm(request.GET)
    qs   = Conductor.objects.all()

    if form.is_valid():
        q     = form.cleaned_data.get('q', '')
        grupo = form.cleaned_data.get('grupo', '')
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) |
                Q(apellido__icontains=q) |
                Q(comunidad__icontains=q) |
                Q(numero_contacto_adulto__icontains=q)
            )
        if grupo:
            qs = qs.filter(grupo=grupo)

    stats_grupos = (
        Conductor.objects.values('grupo')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    context = {
        'conductores':  qs,
        'form':         form,
        'total':        qs.count(),
        'stats_grupos': stats_grupos,
        'grupos_dict':  dict(GRUPOS),
        'google_auth':  google_service.is_authenticated(),
        'google_email': google_service.get_user_email() if google_service.is_authenticated() else '',
        'logs':         SincronizacionLog.objects.all()[:5],
    }
    return render(request, 'conductores/lista.html', context)


def reporte_asistencia(request):
    reporte = (
        Conductor.objects.values('grupo')
        .annotate(
            total_dia_1=Count('id', filter=Q(asistencia_dia_1=True)),
            total_dia_2=Count('id', filter=Q(asistencia_dia_2=True)),
            total_dia_3=Count('id', filter=Q(asistencia_dia_3=True)),
            total_conductores=Count('id')
        )
        .order_by('-total_conductores')
    )
    
    grupos_dict = dict(GRUPOS)
    for r in reporte:
        r['grupo_display'] = grupos_dict.get(r['grupo'], r['grupo'])

    totales = {
        'conductores': sum(r['total_conductores'] for r in reporte),
        'dia_1': sum(r['total_dia_1'] for r in reporte),
        'dia_2': sum(r['total_dia_2'] for r in reporte),
        'dia_3': sum(r['total_dia_3'] for r in reporte),
    }

    return render(request, 'conductores/reporte_asistencia.html', {
        'reporte': reporte,
        'totales': totales,
        'titulo': 'Reporte de Asistencia por Grupo'
    })



# ── ABM ───────────────────────────────────────────────────────────────────────

def crear(request):
    if request.method == 'POST':
        form = ConductorForm(request.POST)
        if form.is_valid():
            conductor = form.save()
            messages.success(request, f'✔ {conductor.nombre_completo} registrado correctamente.')
            return redirect('conductores:detalle', pk=conductor.pk)
    else:
        form = ConductorForm()
    return render(request, 'conductores/form.html', {'form': form, 'titulo': 'Nuevo participante'})


def detalle(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    return render(request, 'conductores/detalle.html', {'conductor': conductor, 'grupos': GRUPOS})


def editar(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    if request.method == 'POST':
        form = ConductorForm(request.POST, instance=conductor)
        if form.is_valid():
            form.save()
            messages.success(request, f'✔ {conductor.nombre_completo} actualizado.')
            return redirect('conductores:detalle', pk=pk)
    else:
        form = ConductorForm(instance=conductor)
    return render(request, 'conductores/form.html', {
        'form': form,
        'conductor': conductor,
        'titulo': f'Editar participante – {conductor.nombre_completo}',
    })


@require_POST
def eliminar(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    nombre = conductor.nombre_completo
    conductor.delete()
    messages.success(request, f'🗑 {nombre} eliminado.')
    return redirect('conductores:lista')


@require_POST
def cambiar_grupo(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    grupo     = request.POST.get('grupo', 'sin_asignar')
    conductor.grupo = grupo
    conductor.save(update_fields=['grupo', 'actualizado_en'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'grupo': conductor.grupo_display})
    messages.success(request, f'Grupo actualizado a {conductor.grupo_display}.')
    return redirect('conductores:detalle', pk=pk)


@require_POST
def actualizar_asistencia(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    conductor.asistencia_dia_1 = request.POST.get('asistencia_dia_1') == 'on'
    conductor.asistencia_dia_2 = request.POST.get('asistencia_dia_2') == 'on'
    conductor.asistencia_dia_3 = request.POST.get('asistencia_dia_3') == 'on'
    conductor.save(update_fields=['asistencia_dia_1', 'asistencia_dia_2', 'asistencia_dia_3', 'actualizado_en'])
    messages.success(request, f'Asistencia actualizada para {conductor.nombre_completo}.')
    return redirect('conductores:detalle', pk=pk)


# ── EXPORTAR EXCEL LOCAL ──────────────────────────────────────────────────────

def exportar_excel(request):
    filtro = request.GET.get('grupo', '')
    qs = Conductor.objects.filter(grupo=filtro) if filtro else Conductor.objects.all()

    buffer   = excel_service.exportar_excel(qs)
    filename = f'conductores_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    SincronizacionLog.objects.create(
        tipo='export', registros=qs.count(),
        archivo=filename, exitoso=True,
        mensaje='Exportación Excel local'
    )

    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── IMPORTAR EXCEL ────────────────────────────────────────────────────────────

def importar_excel(request):
    if request.method == 'POST':
        form = ImportarExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo']
            try:
                datos  = excel_service.importar_excel(archivo)
                creados = 0
                for row in datos:
                    Conductor.objects.create(**row)
                    creados += 1
                SincronizacionLog.objects.create(
                    tipo='import', registros=creados,
                    archivo=archivo.name, exitoso=True,
                    mensaje='Importación desde Excel'
                )
                messages.success(request, f'✔ {creados} participantes importados correctamente.')
            except Exception as e:
                messages.error(request, f'Error al importar: {e}')
            return redirect('conductores:lista')
    else:
        form = ImportarExcelForm()
    return render(request, 'conductores/importar.html', {'form': form})


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────

def google_auth(request):
    url, state = google_service.get_auth_url()
    if not url:
        messages.error(request, 'No se pudo iniciar autenticación con Google.')
        return redirect('conductores:lista')
    request.session['google_oauth_state'] = state
    return redirect(url)


def google_callback(request):
    code  = request.GET.get('code')
    state = request.GET.get('state')
    if not code:
        messages.error(request, 'Error en autenticación con Google.')
        return redirect('conductores:lista')
    try:
        google_service.handle_oauth_callback(code, state)
        messages.success(request, '✔ Sesión con Google iniciada correctamente.')
    except Exception as e:
        messages.error(request, f'Error: {e}')
    return redirect('conductores:lista')


def google_logout(request):
    google_service.revoke_token()
    messages.info(request, 'Sesión de Google cerrada.')
    return redirect('conductores:lista')


def exportar_sheets(request):
    if not google_service.is_authenticated():
        messages.warning(request, 'Primero debes conectar tu cuenta de Google.')
        return redirect('conductores:lista')
    try:
        qs = Conductor.objects.all()
        sid, n = google_service.export_to_sheets(qs)
        url = f'https://docs.google.com/spreadsheets/d/{sid}'
        SincronizacionLog.objects.create(
            tipo='export', registros=n,
            archivo=url, exitoso=True,
            usuario_google=google_service.get_user_email(),
            mensaje='Exportación a Google Sheets'
        )
        messages.success(request, f'✔ {n} registros exportados a Google Sheets.')
    except Exception as e:
        messages.error(request, f'Error al exportar: {e}')
    return redirect('conductores:lista')


def importar_sheets(request):
    if not google_service.is_authenticated():
        messages.warning(request, 'Primero debes conectar tu cuenta de Google.')
        return redirect('conductores:lista')
    try:
        datos   = google_service.import_from_sheets()
        creados = 0
        for row in datos:
            Conductor.objects.update_or_create(
                nombre=row['nombre'], apellido=row['apellido'],
                defaults=row,
            )
            creados += 1
        SincronizacionLog.objects.create(
            tipo='import', registros=creados,
            exitoso=True,
            usuario_google=google_service.get_user_email(),
            mensaje='Importación desde Google Sheets'
        )
        messages.success(request, f'✔ {creados} participantes importados desde Google Sheets.')
    except Exception as e:
        messages.error(request, f'Error al importar: {e}')
    return redirect('conductores:lista')
