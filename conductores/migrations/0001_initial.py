from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Conductor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre')),
                ('apellido', models.CharField(max_length=100, verbose_name='Apellido')),
                ('edad', models.PositiveSmallIntegerField(verbose_name='Edad')),
                ('direccion', models.TextField(verbose_name='Dirección')),
                ('nombre_padres', models.CharField(max_length=200, verbose_name='Nombre de los padres/tutores')),
                ('numero_contacto_adulto', models.CharField(max_length=30, verbose_name='Número de contacto adulto')),
                ('comunidad', models.CharField(max_length=150, verbose_name='Comunidad')),
                ('dificultades', models.TextField(blank=True, verbose_name='Dificultades / necesidades especiales')),
                ('fecha_recepcion', models.DateField(default=django.utils.timezone.now, verbose_name='Fecha de recepción')),
                ('grupo', models.CharField(
                    choices=[
                        ('sin_asignar', 'Sin asignar'),
                        ('grupo_a', 'Grupo A'),
                        ('grupo_b', 'Grupo B'),
                        ('grupo_c', 'Grupo C'),
                        ('grupo_d', 'Grupo D'),
                        ('grupo_e', 'Grupo E'),
                        ('especial', 'Grupo Especial'),
                        ('espera', 'En espera'),
                    ],
                    default='sin_asignar',
                    max_length=30,
                    verbose_name='Grupo',
                )),
                ('creado_en', models.DateTimeField(auto_now_add=True, verbose_name='Creado en')),
                ('actualizado_en', models.DateTimeField(auto_now=True, verbose_name='Actualizado en')),
            ],
            options={
                'verbose_name': 'Conductor',
                'verbose_name_plural': 'Conductores',
                'ordering': ['-creado_en'],
            },
        ),
        migrations.CreateModel(
            name='SincronizacionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('export', 'Exportación'), ('import', 'Importación')], max_length=10)),
                ('registros', models.PositiveIntegerField(default=0)),
                ('archivo', models.CharField(blank=True, max_length=255)),
                ('usuario_google', models.CharField(blank=True, max_length=200)),
                ('exitoso', models.BooleanField(default=True)),
                ('mensaje', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Log de sincronización',
                'verbose_name_plural': 'Logs de sincronización',
                'ordering': ['-creado_en'],
            },
        ),
    ]
