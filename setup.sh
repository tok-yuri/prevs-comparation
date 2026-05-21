#!/bin/bash
# Cria o ambiente virtual em .env e instala as dependências

set -e

VENV_DIR=".env"

if [ ! -d "$VENV_DIR" ]; then
    echo "Criando ambiente virtual em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Ambiente virtual já existe em $VENV_DIR."
fi

PIP="$VENV_DIR/bin/pip"

echo "Instalando dependências..."
"$PIP" install --upgrade pip

echo "Instalando backends de autenticação..."
"$PIP" install keyring keyrings.google-artifactregistry-auth

echo "Instalando demais dependências..."
"$PIP" install -r requirements.txt

echo "Ambiente pronto. Para ativar: source $VENV_DIR/bin/activate"
