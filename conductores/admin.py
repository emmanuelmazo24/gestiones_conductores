from django.contrib import admin
from .models import Conductor, SincronizacionLog


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display  = ('nombre_completo', 'edad', 'comunidad', 'grupo', 'fecha_recepcion', 'creado_en')
    list_filter   = ('grupo', 'comunidad')
    search_fields = ('nombre', 'apellido', 'comunidad', 'numero_contacto_adulto')
    list_editable = ('grupo',)
    date_hierarchy = 'fecha_recepcion'
    readonly_fields = ('creado_en', 'actualizado_en')

    fieldsets = (
        ('Datos personales', {
            'fields': ('nombre', 'apellido', 'edad', 'direccion')
        }),
        ('Familia y contacto', {
            'fields': ('nombre_padres', 'numero_contacto_adulto')
        }),
        ('Comunidad', {
            'fields': ('comunidad', 'dificultades')
        }),
        ('Gestión', {
            'fields': ('fecha_recepcion', 'grupo')
        }),
        ('Metadata', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SincronizacionLog)
class SincronizacionLogAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'registros', 'exitoso', 'usuario_google', 'creado_en')
    list_filter  = ('tipo', 'exitoso')
    readonly_fields = ('creado_en',)
