from django.db import models
from django.utils import timezone


GRUPOS = [
    ('sin_asignar', 'Sin asignar'),
    ('grupo_a',     'Santa Teresita del Niño Jesús'),
    ('grupo_b',     'San Carlo Acutis'),
    ('grupo_c',     'San Pier Giorgio'),
    ('grupo_d',     'San Domingo Savio'),
    ('grupo_e',     'Beata Chiara Luce Badano'),
    ('grupo_f',    'Sierva de Dios Clare Crockett'),
    ('grupo_g',      'Beato Rolando Rivi'),
    ('grupo_h',      'Siervo de Dios Marcelo Câmara'),
    ('grupo_i',      'San Luis Gonzaga'),
]


class Conductor(models.Model):
    # Datos personales
    nombre                 = models.CharField('Nombre',          max_length=100)
    apellido               = models.CharField('Apellido',        max_length=100)
    edad                   = models.PositiveSmallIntegerField('Edad')
    cedula                 = models.CharField('Cedula',          max_length=20,null=True,blank=True)
    direccion              = models.TextField('Dirección')

    # Familia y contacto
    nombre_padres          = models.CharField('Nombre de los padres/tutores', max_length=200)
    numero_contacto_adulto = models.CharField('Número de contacto adulto',   max_length=30)

    # Comunidad
    comunidad              = models.CharField('Comunidad', max_length=150)

    # Observaciones
    dificultades           = models.TextField('Dificultades / necesidades especiales', blank=True)

    # Gestión
    fecha_recepcion        = models.DateField('Fecha de recepción', default=timezone.now)
    grupo                  = models.CharField('Grupo', max_length=30,
                                              choices=GRUPOS, default='sin_asignar')

    # Metadatos
    creado_en              = models.DateTimeField('Creado en',      auto_now_add=True)
    actualizado_en         = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name        = 'Conductor'
        verbose_name_plural = 'Conductores'
        ordering            = ['-creado_en']

    def __str__(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'

    @property
    def grupo_display(self):
        return dict(GRUPOS).get(self.grupo, self.grupo)

    def to_row(self):
        """Retorna una lista para exportar a Excel/Sheets."""
        return [
            self.pk,
            self.nombre,
            self.apellido,
            self.edad,
            self.direccion,
            self.nombre_padres,
            self.numero_contacto_adulto,
            self.comunidad,
            self.dificultades,
            self.fecha_recepcion.strftime('%d/%m/%Y') if self.fecha_recepcion else '',
            self.grupo_display,
            self.creado_en.strftime('%d/%m/%Y %H:%M') if self.creado_en else '',
        ]

    @classmethod
    def headers(cls):
        return [
            'ID', 'Nombre', 'Apellido', 'Edad', 'Dirección',
            'Nombre Padres/Tutores', 'Contacto Adulto', 'Comunidad',
            'Dificultades', 'Fecha Recepción', 'Grupo', 'Registrado en',
        ]


class SincronizacionLog(models.Model):
    TIPOS = [
        ('export', 'Exportación'),
        ('import', 'Importación'),
    ]
    tipo          = models.CharField(max_length=10, choices=TIPOS)
    registros     = models.PositiveIntegerField(default=0)
    archivo       = models.CharField(max_length=255, blank=True)
    usuario_google = models.CharField(max_length=200, blank=True)
    exitoso       = models.BooleanField(default=True)
    mensaje       = models.TextField(blank=True)
    creado_en     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Log de sincronización'
        verbose_name_plural = 'Logs de sincronización'
        ordering            = ['-creado_en']

    def __str__(self):
        return f'{self.get_tipo_display()} – {self.creado_en:%d/%m/%Y %H:%M}'
