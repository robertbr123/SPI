#!/usr/bin/env bash
set -euo pipefail

# Linux-ready runner for local dev

# Carregar .env se existir (formato KEY=VALUE, sem aspas)
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

# Verificar python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 não encontrado. Instale o Python 3." >&2
  exit 1
fi

# Criar venv se não existir
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# Ativar venv (Linux)
source .venv/bin/activate

# Atualizar pip e instalar deps
pip install --upgrade pip
pip install -r requirements.txt

# Migrações e rodar servidor
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
