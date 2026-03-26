#!/usr/bin/env bash
# setup.sh — configura el proyecto desde cero

set -e

echo "=== Gestión de Conductores — Setup ==="

# 1. Entorno virtual
if [ ! -d "venv" ]; then
  echo "[1/4] Creando entorno virtual..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "[2/4] Instalando dependencias..."
pip install -r requirements.txt --quiet

# 2. Migraciones
echo "[3/4] Creando base de datos SQLite..."
python manage.py migrate --run-syncdb

# 3. Superusuario
echo "[4/4] Creando superusuario para /admin/ ..."
python manage.py createsuperuser --noinput \
  --username admin \
  --email admin@local.com 2>/dev/null || echo "  (ya existe, se omite)"

echo ""
echo "✔ Listo. Ejecutá:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo "   Abrí: http://localhost:8000"
