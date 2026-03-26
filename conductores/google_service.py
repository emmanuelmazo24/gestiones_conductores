"""
Servicio de integración con Google Drive / Sheets.
Usa OAuth2 con flujo web para autenticación del usuario.
"""
import json
import os
from pathlib import Path

from django.conf import settings

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'openid',
    'email',
    'profile',
]

TOKEN_FILE = Path(settings.TOKEN_DIR) / 'google_token.json'
CLIENT_SECRETS = {
    "web": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def _load_credentials():
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE) as f:
        data = json.load(f)
    creds = Credentials(
        token=data.get('token'),
        refresh_token=data.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
    return creds


def _save_credentials(creds):
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        json.dump({
            'token': creds.token,
            'refresh_token': creds.refresh_token,
        }, f)


def get_auth_url():
    """Retorna URL para iniciar OAuth2."""
    if not GOOGLE_AVAILABLE:
        return None, 'Librerías de Google no instaladas'
    flow = Flow.from_client_config(CLIENT_SECRETS, scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    url, state = flow.authorization_url(access_type='offline', prompt='consent')
    return url, state


def handle_oauth_callback(code, state=None):
    """Procesa callback OAuth2 y guarda token."""
    flow = Flow.from_client_config(CLIENT_SECRETS, scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    _save_credentials(flow.credentials)
    return True


def is_authenticated():
    if not GOOGLE_AVAILABLE:
        return False
    try:
        creds = _load_credentials()
        return creds is not None and creds.valid
    except Exception:
        return False


def get_user_email():
    creds = _load_credentials()
    if not creds:
        return ''
    try:
        service = build('oauth2', 'v2', credentials=creds)
        info = service.userinfo().get().execute()
        return info.get('email', '')
    except Exception:
        return ''


def revoke_token():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


# ── GOOGLE SHEETS ──────────────────────────────────────────────────────────────

SPREADSHEET_NAME = 'GestionConductores_DB'
SHEET_NAME = 'Conductores'
_cached_spreadsheet_id = None


def _get_sheets_service():
    creds = _load_credentials()
    if not creds:
        raise Exception('No autenticado con Google')
    return build('sheets', 'v4', credentials=creds)


def _get_drive_service():
    creds = _load_credentials()
    if not creds:
        raise Exception('No autenticado con Google')
    return build('drive', 'v3', credentials=creds)


def _find_or_create_spreadsheet():
    global _cached_spreadsheet_id
    if _cached_spreadsheet_id:
        return _cached_spreadsheet_id

    drive = _get_drive_service()
    results = drive.files().list(
        q=f"name='{SPREADSHEET_NAME}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        spaces='drive',
        fields='files(id, name)',
    ).execute()

    files = results.get('files', [])
    if files:
        _cached_spreadsheet_id = files[0]['id']
        return _cached_spreadsheet_id

    # Crear nueva hoja
    sheets = _get_sheets_service()
    body = {
        'properties': {'title': SPREADSHEET_NAME},
        'sheets': [{'properties': {'title': SHEET_NAME}}],
    }
    spreadsheet = sheets.spreadsheets().create(body=body).execute()
    _cached_spreadsheet_id = spreadsheet['spreadsheetId']

    # Escribir cabeceras
    from .models import Conductor
    sheets.spreadsheets().values().update(
        spreadsheetId=_cached_spreadsheet_id,
        range=f'{SHEET_NAME}!A1',
        valueInputOption='RAW',
        body={'values': [Conductor.headers()]},
    ).execute()

    return _cached_spreadsheet_id


def export_to_sheets(conductores_qs):
    """Exporta queryset a Google Sheets. Retorna (spreadsheet_id, n_filas)."""
    service = _get_sheets_service()
    sid = _find_or_create_spreadsheet()

    # Limpiar datos (conservar header fila 1)
    service.spreadsheets().values().clear(
        spreadsheetId=sid,
        range=f'{SHEET_NAME}!A2:Z',
        body={},
    ).execute()

    rows = [c.to_row() for c in conductores_qs]
    if rows:
        service.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f'{SHEET_NAME}!A2',
            valueInputOption='RAW',
            body={'values': rows},
        ).execute()

    return sid, len(rows)


def import_from_sheets():
    """Importa filas de Google Sheets. Retorna lista de dicts."""
    service = _get_sheets_service()
    sid = _find_or_create_spreadsheet()

    result = service.spreadsheets().values().get(
        spreadsheetId=sid,
        range=f'{SHEET_NAME}!A2:L',
    ).execute()

    values = result.get('values', [])
    conductores = []
    for row in values:
        while len(row) < 12:
            row.append('')
        conductores.append({
            'nombre':                 row[1],
            'apellido':               row[2],
            'edad':                   int(row[3]) if row[3].isdigit() else 0,
            'direccion':              row[4],
            'nombre_padres':          row[5],
            'numero_contacto_adulto': row[6],
            'comunidad':              row[7],
            'dificultades':           row[8],
            'fecha_recepcion':        _parse_date(row[9]),
            'grupo':                  _parse_grupo(row[10]),
        })
    return conductores


def _parse_date(s):
    from datetime import date
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return date.today()


def _parse_grupo(s):
    from .models import GRUPOS
    reverse = {v: k for k, v in dict(GRUPOS).items()}
    return reverse.get(s, 'sin_asignar')


def get_spreadsheet_url():
    sid = _find_or_create_spreadsheet()
    return f'https://docs.google.com/spreadsheets/d/{sid}'
