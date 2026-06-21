#!/usr/bin/env bash
set -e

# Cores para o output elegante
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Sem cor

# Configurações de diretórios (permite sobrescrever via variáveis de ambiente)
SRC_DIR="${SRC_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
PLUGINS_DIR="${PLUGINS_DIR:-/app/volumes/navidrome/plugins}"
NAV_DB_PATH="${NAV_DB_PATH:-/app/volumes/navidrome/data/navidrome.db}"
NAV_CONTAINER_DIR="${NAV_CONTAINER_DIR:-/app/services/containers/navidrome}"

echo -e "${BLUE}=== Iniciando Compilação e Empacotamento do Plugin Navidrome ===${NC}"

# 1. Validações de Dependências
echo -e "${BLUE}[1/5] Verificando dependências locais...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Erro: Docker não encontrado no host. Por favor, instale o Docker.${NC}"
    exit 1
fi
if ! command -v zip &> /dev/null; then
    echo -e "${RED}Erro: Utilitário 'zip' não encontrado. Por favor, instale o zip (sudo apt install zip).${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dependências locais OK!${NC}"

# 2. Resolução de Dependências Go Mod no TinyGo Docker
echo -e "${BLUE}[2/5] Resolvendo dependências do Go Mod via Docker (TinyGo)...${NC}"
docker run --rm \
  -v "${SRC_DIR}":/src \
  -w /src \
  tinygo/tinygo:latest \
  go mod tidy
echo -e "${GREEN}✓ Dependências do Go resolvidas!${NC}"

# 3. Compilação para WebAssembly (plugin.wasm)
echo -e "${BLUE}[3/5] Compilando plugin Go para WebAssembly (TinyGo)...${NC}"
docker run --rm \
  -v "${SRC_DIR}":/src \
  -w /src \
  tinygo/tinygo:latest \
  tinygo build -o /src/plugin.wasm -target wasip1 -buildmode=c-shared /src/plugin.go
echo -e "${GREEN}✓ Arquivo plugin.wasm compilado com sucesso!${NC}"

# 4. Empacotamento para formato .ndp
echo -e "${BLUE}[4/5] Empacotando manifest.json e plugin.wasm em .ndp...${NC}"
cd "${SRC_DIR}"
zip -j spotify-sync.ndp manifest.json plugin.wasm
echo -e "${GREEN}✓ Pacote spotify-sync.ndp gerado com sucesso!${NC}"

# 5. Instalação e Reinicialização do Contêiner
echo -e "${BLUE}[5/5] Instalando plugin no Navidrome e aplicando configurações...${NC}"
if [ -d "${PLUGINS_DIR}" ]; then
    # Copiar pacote .ndp
    cp spotify-sync.ndp "${PLUGINS_DIR}/spotify-sync.ndp"
    echo -e "${GREEN}✓ Pacote copiado para a pasta de plugins do Navidrome.${NC}"
    
    # Reiniciar contêiner de forma limpa (parar, atualizar banco para evitar sobrescritas, iniciar)
    if [ -d "${NAV_CONTAINER_DIR}" ] && [ -f "${NAV_CONTAINER_DIR}/docker-compose.yml" ]; then
        echo -e "${YELLOW}Parando o contêiner do Navidrome para desbloquear banco SQLite...${NC}"
        cd "${NAV_CONTAINER_DIR}"
        docker compose stop
        
        if [ -f "${NAV_DB_PATH}" ]; then
            echo -e "${YELLOW}Garantindo ativação do plugin no banco de dados SQLite...${NC}"
            sqlite3 "${NAV_DB_PATH}" "UPDATE plugin SET enabled = 1 WHERE id = 'spotify-sync';"
            echo -e "${GREEN}✓ Plugin definido como ativado (enabled = 1) no banco.${NC}"
        fi
        
        echo -e "${YELLOW}Iniciando contêiner do Navidrome...${NC}"
        docker compose start
        echo -e "${GREEN}✓ Contêiner reiniciado com sucesso!${NC}"
    else
        echo -e "${YELLOW}Aviso: Diretório do docker-compose do Navidrome não encontrado em ${NAV_CONTAINER_DIR}. Reinicie o contêiner manualmente para carregar o plugin.${NC}"
    fi
else
    echo -e "${YELLOW}Aviso: Diretório de plugins do Navidrome não encontrado em ${PLUGINS_DIR}. Instalação automática pulada.${NC}"
fi

echo -e "${GREEN}=== Processo concluído com sucesso! ===${NC}"
