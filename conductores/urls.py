from django.urls import path
from . import views
from . import public_sheets_views

app_name = 'conductores'

urlpatterns = [
    # Lista y ABM
    path('',                    views.lista,         name='lista'),
    path('nuevo/',              views.crear,         name='crear'),
    path('<int:pk>/',           views.detalle,       name='detalle'),
    path('<int:pk>/editar/',    views.editar,        name='editar'),
    path('<int:pk>/eliminar/',  views.eliminar,      name='eliminar'),
    path('<int:pk>/grupo/',     views.cambiar_grupo, name='cambiar_grupo'),
    path('<int:pk>/asistencia/', views.actualizar_asistencia, name='actualizar_asistencia'),
    path('reporte-asistencia/', views.reporte_asistencia, name='reporte_asistencia'),

    # Excel local
    path('exportar/excel/',     views.exportar_excel, name='exportar_excel'),
    path('importar/excel/',     views.importar_excel, name='importar_excel'),

    # Google Sheets
    path('google/auth/',        views.google_auth,      name='google_auth'),
    path('oauth2callback/',     views.google_callback,  name='google_callback'),
    path('google/logout/',      views.google_logout,    name='google_logout'),
    path('google/exportar/',    views.exportar_sheets,  name='exportar_sheets'),
    path('google/importar/',    views.importar_sheets,  name='importar_sheets'),

    # Hoja pública (sin OAuth)
    path('hoja-publica/',           public_sheets_views.hoja_publica,                 name='hoja_publica'),
    path('hoja-publica/preview/',   public_sheets_views.hoja_publica_preview,         name='hoja_publica_preview'),
    path('hoja-publica/importar/',  public_sheets_views.hoja_publica_importar,        name='hoja_publica_importar'),
    path('hoja-publica/excel/',     public_sheets_views.hoja_publica_exportar_preview, name='hoja_publica_exportar_preview'),
]
