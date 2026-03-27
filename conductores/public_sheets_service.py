"""
public_sheets_service.py
========================
Extracción de datos desde Google Sheets públicas.

Método A — CSV directo (sin credenciales)
    URL: https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid={GID}

Método B — Sheets API v4 con API Key
    URL: https://sheets.googleapis.com/v4/spreadsheets/{ID}/values/{RANGE}?key={APIKEY}

Ambos métodos detectan automáticamente los encabezados y mapean columnas
al modelo Conductor usando coincidencia flexible de nombres.
"""

import csv
import io
import re
import urllib.request
import urllib.error
import json
from datetime import date, datetime

# ── UTILIDADES ────────────────────────────────────────────────────────────────

def extraer_id_desde_url(url: str) -> str:
    """
    Acepta la URL completa de Google Sheets o solo el ID.
    Ejemplos válidos:
      https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
      1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
    """
    url = url.strip()
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    # Si ya es el ID directo
    if re.match(r'^[a-zA-Z0-9_-]{20,}$', url):
        return url
    raise ValueError(f'No se pudo extraer el ID de la hoja: {url!r}')


def extraer_gid_desde_url(url: str) -> str:
    """Extrae el gid (id de pestaña) de la URL si está presente."""
    match = re.search(r'[#&?]gid=(\d+)', url)
    return match.group(1) if match else '0'


# ── MAPEO FLEXIBLE DE COLUMNAS ────────────────────────────────────────────────

# Sinónimos aceptados para cada campo del modelo Conductor
COLUMN_MAP = {
    'nombre':                 ['nombre', 'name', 'first name', 'primer nombre'],
    'apellido':               ['apellido', 'lastname', 'last name', 'surname', 'segundo nombre'],
    'cedula':                 ['cedula', 'cedula', 'dni', 'documento', 'documento de identidad', 'documento identidad'],
    'edad':                   ['edad', 'age', 'años'],
    'direccion':              ['direccion', 'dirección', 'address', 'domicilio'],
    'nombre_padres':          ['nombre_padres', 'padres', 'tutores', 'nombre padres',
                               'nombre de los padres', 'padre/madre', 'parents','Nombre Padres/Tutores'],
    'numero_contacto_adulto': ['numero_contacto_adulto', 'contacto', 'telefono', 'teléfono',
                               'número contacto', 'numero contacto', 'phone', 'contact','Contacto Adulto'],
    'comunidad':              ['comunidad', 'community', 'barrio', 'localidad', 'zona'],
    'dificultades':           ['dificultades', 'difficulties', 'necesidades', 'observaciones',
                               'notas', 'notes', 'remarks'],
    'fecha_recepcion':        ['fecha_recepcion', 'fecha recepcion', 'fecha de recepción',
                               'fecha', 'date', 'reception date', 'fecha ingreso','Fecha Recepción'],
    'grupo':                  ['grupo', 'group', 'equipo', 'team', 'clase'],
}

GRUPOS_REVERSE = {
    'sin asignar': 'sin_asignar', 'sin_asignar': 'sin_asignar',
    'grupo a': 'grupo_a', 'grupo_a': 'grupo_a', 'a': 'grupo_a',
    'grupo b': 'grupo_b', 'grupo_b': 'grupo_b', 'b': 'grupo_b',
    'grupo c': 'grupo_c', 'grupo_c': 'grupo_c', 'c': 'grupo_c',
    'grupo d': 'grupo_d', 'grupo_d': 'grupo_d', 'd': 'grupo_d',
    'grupo e': 'grupo_e', 'grupo_e': 'grupo_e', 'e': 'grupo_e',
    'especial': 'especial', 'grupo especial': 'especial',
    'espera': 'espera', 'en espera': 'espera',
}


def _map_headers(raw_headers: list) -> dict:
    """
    Dado una lista de encabezados del sheet, retorna un dict
    { campo_modelo: índice_columna } para los campos que se encuentren.
    """
    mapping = {}
    for idx, h in enumerate(raw_headers):
        h_clean = h.strip().lower().replace('-', '_').replace('/', '_')
        for field, synonyms in COLUMN_MAP.items():
            if h_clean in [s.lower() for s in synonyms]:
                if field not in mapping:
                    mapping[field] = idx
                break
    return mapping


def _parse_date(value: str) -> date:
    value = str(value).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return date.today()


def _parse_grupo(value: str) -> str:
    return GRUPOS_REVERSE.get(str(value).strip().lower(), 'sin_asignar')


def _row_to_dict(row: list, mapping: dict, raw_headers: list) -> dict:
    """Convierte una fila a dict de campos del modelo."""
    def get(field):
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return ''
        return str(row[idx]).strip()

    return {
        'nombre':                 get('nombre'),
        'apellido':               get('apellido'),
        'edad':                   int(get('edad') or 0) if get('edad').isdigit() else 0,
        'direccion':              get('direccion'),
        'nombre_padres':          get('nombre_padres'),
        'numero_contacto_adulto': get('numero_contacto_adulto'),
        'comunidad':              get('comunidad'),
        'dificultades':           get('dificultades'),
        'fecha_recepcion':        (_parse_date(get('fecha_recepcion')) if get('fecha_recepcion') else date.today()).isoformat(),
        'grupo':                  _parse_grupo(get('grupo')) if get('grupo') else 'sin_asignar',
        # Columnas originales para la previsualización
        'raw_data': {h: (row[i] if i < len(row) else '') for i, h in enumerate(raw_headers)},
    }


# ── MÉTODO A: CSV DIRECTO ─────────────────────────────────────────────────────

def fetch_csv(spreadsheet_id: str, gid: str = '0', timeout: int = 15) -> dict:
    """
    Descarga la hoja como CSV sin necesidad de credenciales.
    La hoja debe ser pública (cualquiera con el enlace puede verla).

    Retorna:
        {
            'ok': bool,
            'error': str | None,
            'headers': [...],
            'rows': [...],          # filas como listas de strings
            'mapping': {...},       # campo → índice
            'conductores': [...],   # dicts listos para el modelo
            'total': int,
            'metodo': 'csv',
        }
    """
    url = (
        f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}'
        f'/export?format=csv&gid={gid}'
    )
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return {'ok': False, 'error': f'HTTP {resp.status}'}
            content = resp.read().decode('utf-8-sig')
    except urllib.error.HTTPError as e:
        if e.code == 302:
            return {'ok': False, 'error': 'La hoja no es pública o el ID es incorrecto.'}
        return {'ok': False, 'error': f'HTTP {e.code}: {e.reason}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    reader   = csv.reader(io.StringIO(content))
    all_rows = list(reader)

    if not all_rows:
        return {'ok': False, 'error': 'La hoja está vacía.'}

    headers    = all_rows[0]
    data_rows  = [r for r in all_rows[1:] if any(c.strip() for c in r)]
    mapping    = _map_headers(headers)
    conductores = [_row_to_dict(r, mapping, headers) for r in data_rows]

    return {
        'ok': True, 'error': None,
        'headers': headers, 'rows': data_rows,
        'mapping': mapping, 'conductores': conductores,
        'total': len(conductores), 'metodo': 'csv',
        'url_usada': url,
    }


# ── MÉTODO B: SHEETS API v4 CON API KEY ───────────────────────────────────────

def fetch_api_key(spreadsheet_id: str, api_key: str,
                  rango: str = 'A:Z', timeout: int = 15) -> dict:
    """
    Usa la Sheets API v4 con una API Key pública (sin OAuth).
    Requiere que la hoja sea pública Y que la API Key esté habilitada
    para Google Sheets API en Google Cloud Console.

    Retorna la misma estructura que fetch_csv().
    """
    url = (
        f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}'
        f'/values/{rango}?key={api_key}'
    )
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            err_data = json.loads(body)
            msg = err_data.get('error', {}).get('message', str(e))
        except Exception:
            msg = str(e)
        return {'ok': False, 'error': msg}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    values = data.get('values', [])
    if not values:
        return {'ok': False, 'error': 'La hoja está vacía o el rango no existe.'}

    headers    = values[0]
    data_rows  = [r for r in values[1:] if any(c.strip() for c in r)]
    mapping    = _map_headers(headers)
    conductores = [_row_to_dict(r, mapping, headers) for r in data_rows]

    return {
        'ok': True, 'error': None,
        'headers': headers, 'rows': data_rows,
        'mapping': mapping, 'conductores': conductores,
        'total': len(conductores), 'metodo': 'api_key',
        'url_usada': url.split('?')[0],  # ocultar la key en logs
    }


# ── EXTRACTOR UNIFICADO ───────────────────────────────────────────────────────

def extraer_desde_hoja_publica(url_o_id: str,
                                api_key: str = '',
                                rango: str = 'A:Z') -> dict:
    """
    Punto de entrada principal. Intenta primero CSV; si falla y hay
    API key, intenta con Sheets API.
    """
    try:
        sheet_id = extraer_id_desde_url(url_o_id)
        gid      = extraer_gid_desde_url(url_o_id)
        print(sheet_id)
        print(gid)
    except ValueError as e:
        print(str(e))
        return {'ok': False, 'error': str(e)}

    result = fetch_csv(sheet_id, gid)

    if not result['ok'] and api_key:
        result = fetch_api_key(sheet_id, api_key, rango)

    result['sheet_id'] = sheet_id
    result['gid']      = gid
    return result
