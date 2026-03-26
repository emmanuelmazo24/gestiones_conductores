# 🚗 Gestión de Conductores — Django

Sistema web completo para registrar, listar, buscar y gestionar conductores.
Incluye exportación/importación a **Excel local** y a **Google Sheets** vía Drive API.

---

## ✨ Funcionalidades

| Módulo | Detalle |
|---|---|
| **ABM completo** | Alta, baja y modificación de conductores |
| **Lista con filtros** | Búsqueda por nombre / comunidad y filtro por grupo |
| **Cambio de grupo** | Modal rápido desde la lista o el detalle |
| **Excel local** | Descarga `.xlsx` con formato, colores por grupo y hoja de resumen |
| **Importar Excel** | Carga masiva desde el mismo formato exportado |
| **Google Sheets** | Exporta/importa todos los registros a una hoja de tu Drive |
| **Logs** | Registro de cada sincronización (quién, cuántos, cuándo) |
| **Admin Django** | Panel `/admin/` para gestión avanzada |

### Campos registrados
- Nombre y Apellido
- Edad
- Dirección
- Nombre de los Padres/Tutores
- Número de Contacto Adulto
- Comunidad
- Dificultades / necesidades especiales
- Fecha de Recepción
- Grupo asignado

---

## 🛠 Instalación rápida

### 1. Crear entorno virtual e instalar dependencias

```bash
cd gestion_conductores
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Crear la base de datos local

```bash
python manage.py migrate
python manage.py createsuperuser   # opcional — para el panel /admin/
```

### 3. Ejecutar el servidor

```bash
python manage.py runserver
```

Abrí el navegador en **http://localhost:8000**

---

## 🔑 Configurar Google Drive / Sheets (opcional)

Si no necesitás Google Drive, la app funciona 100% en modo local (Excel).

### Paso 1 — Crear proyecto en Google Cloud Console

1. Ir a [console.cloud.google.com](https://console.cloud.google.com)
2. Crear un nuevo proyecto
3. Activar las APIs:
   - **Google Drive API**
   - **Google Sheets API**
   - **Google OAuth2 API** (`oauth2`)

### Paso 2 — Crear credenciales OAuth 2.0

1. *APIs y servicios → Credenciales → Crear credencial → ID de cliente OAuth 2.0*
2. Tipo: **Aplicación web**
3. Agregar URI de redireccionamiento autorizado:
   ```
   http://localhost:8000/conductores/oauth2callback/
   ```
4. Descargar JSON de credenciales

### Paso 3 — Configurar pantalla de consentimiento

En *Pantalla de consentimiento OAuth*, agregar los ámbitos (scopes):
- `https://www.googleapis.com/auth/drive.file`
- `https://www.googleapis.com/auth/spreadsheets`

### Paso 4 — Variables de entorno

Crear archivo `.env` en la raíz (o exportar manualmente):

```bash
export GOOGLE_CLIENT_ID="tu-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="tu-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:8000/conductores/oauth2callback/"
```

En Windows (PowerShell):
```powershell
$env:GOOGLE_CLIENT_ID="tu-client-id.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET="tu-client-secret"
$env:GOOGLE_REDIRECT_URI="http://localhost:8000/conductores/oauth2callback/"
```

Luego iniciar el servidor y hacer clic en **"Conectar con Google"** en el menú lateral.

---

## 📁 Estructura del proyecto

```
gestion_conductores/
├── manage.py
├── requirements.txt
├── db.sqlite3                    ← se crea al migrar
├── tokens/                       ← tokens OAuth (auto-creado)
│
├── gestion_conductores/
│   ├── settings.py
│   └── urls.py
│
└── conductores/
    ├── models.py                 ← Conductor + SincronizacionLog
    ├── views.py                  ← Lista, ABM, exportar, importar
    ├── forms.py                  ← Formularios Django
    ├── urls.py                   ← Rutas
    ├── admin.py                  ← Panel admin
    ├── excel_service.py          ← Exportación/importación Excel (openpyxl)
    ├── google_service.py         ← Google OAuth2 + Sheets API
    ├── migrations/
    └── templates/conductores/
        ├── base.html             ← Layout con sidebar
        ├── lista.html            ← Lista + filtros + stats
        ├── form.html             ← Alta / edición
        ├── detalle.html          ← Vista detalle + cambio de grupo
        └── importar.html         ← Importar Excel
```

---

## 🎨 Grupos disponibles

Editar `conductores/models.py` → constante `GRUPOS`:

```python
GRUPOS = [
    ('sin_asignar', 'Sin asignar'),
    ('grupo_a',     'Grupo A'),
    ...
]
```

Después de editar, ejecutar:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 📊 Exportación Excel

El archivo `.xlsx` descargado incluye:
- **Hoja "Conductores"**: todos los registros con formato, colores por grupo, filtros automáticos y filas congeladas
- **Hoja "Resumen por Grupo"**: tabla resumen con cantidad y porcentaje por grupo

---

## 🔄 Flujo Google Sheets

1. El usuario hace clic en **"Conectar con Google"** → se redirige a Google OAuth
2. Tras autorizar, se guarda el token en `tokens/google_token.json`
3. **Exportar**: sube todos los registros locales a una hoja llamada `GestionConductores_DB` en el Drive del usuario (la crea si no existe)
4. **Importar**: descarga los datos de esa hoja y los sincroniza (upsert) en SQLite

---

## 🐛 Problemas comunes

| Problema | Solución |
|---|---|
| `ModuleNotFoundError: google` | `pip install google-api-python-client google-auth-oauthlib` |
| `redirect_uri_mismatch` | Verificar que el URI en Google Console coincide exactamente |
| `403 Forbidden` en Sheets | Activar Google Sheets API en el proyecto de Google Cloud |
| Error al importar Excel | Verificar que el archivo tiene el mismo formato que el exportado |
