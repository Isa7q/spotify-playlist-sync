# Compilação e Empacotamento do Plugin (`spotify-sync`)

Este guia prático fornece instruções detalhadas para desenvolvedores e usuários avançados que desejam compilar o plugin WebAssembly (`plugin.wasm`), empacotá-lo no formato `.ndp` do Navidrome e gerenciar as dependências de build localmente ou em contêineres.

---

## 🛠️ Requisitos da Toolchain de Build

Para compilar e empacotar o projeto a partir do código fonte, as seguintes ferramentas devem estar disponíveis:

1. **Docker**: Utilizado para compilações limpas, evitando a necessidade de instalar compiladores específicos localmente.
2. **Go** (Versão 1.21 ou superior): Para o gerenciamento de módulos e dependências do compilador do Go.
3. **TinyGo** (Versão 0.30.0 ou superior): Compilador Go especializado para WebAssembly (target `wasip1`), gerando binários Wasm ultraleves e de alta performance.
4. **zip**: Utilitário para empacotamento dos arquivos de manifesto e binários.
5. **sqlite3**: Necessário caso use scripts automáticos de atualização de banco.

---

## 🚀 Método 1: Build Totalmente Automatizado (`build.sh`)

O projeto inclui o script de shell unificado **[build.sh](file:///home/isa7q/navidrome-plugin-spotify-sync/build.sh)**. Ele automatiza 100% do processo de validação de dependências, resolução de módulos, compilação para WebAssembly via Docker, geração do zip `.ndp`, cópia do arquivo e reativação segura no banco de dados SQLite do Navidrome para evitar travamentos de escrita.

### Como Executar:
1. Abra o arquivo `build.sh` e ajuste os caminhos absolutos das variáveis do seu ambiente, se necessário:
   * `SRC_DIR`: Raiz deste projeto de plugin.
   * `PLUGINS_DIR`: Pasta de plugins mapeada no contêiner do seu Navidrome.
   * `NAV_DB_PATH`: Caminho físico do arquivo `navidrome.db` no host.
   * `NAV_CONTAINER_DIR`: Pasta do Docker Compose do Navidrome para restart limpo.
2. Torne o script executável:
   ```bash
   chmod +x build.sh
   ```
3. Execute o script:
   ```bash
   ./build.sh
   ```

**O que o script faz por trás dos panos?**
1. Valida se o `docker` e o `zip` estão instalados no host.
2. Roda o `go mod tidy` dentro da imagem oficial do TinyGo para obter o `go.sum` sincronizado.
3. Compila o `plugin.go` para Wasm usando TinyGo com os flags `-target wasip1` e `-buildmode=c-shared`.
4. Compacta o manifesto e o binário gerando `spotify-sync.ndp`.
5. Copia o arquivo `.ndp` para a pasta de plugins.
6. **Para o contêiner do Navidrome**, atualiza o banco local SQLite de forma limpa para garantir que o plugin esteja ativado (`enabled = 1`) e reinicia o contêiner.

---

## 🐋 Método 2: Compilação via Docker (Passo a Passo Manual)

Se preferir realizar as etapas manualmente sem rodar o script utilitário, você pode usar a imagem oficial do TinyGo no Docker:

### 1. Inicializar e resolver dependências do Go Mod
```bash
docker run --rm \
  -v /home/isa7q/navidrome-plugin-spotify-sync:/src \
  -w /src \
  tinygo/tinygo:latest \
  go mod tidy
```

### 2. Compilar o plugin Go para WebAssembly
```bash
docker run --rm \
  -v /home/isa7q/navidrome-plugin-spotify-sync:/src \
  -w /src \
  tinygo/tinygo:latest \
  tinygo build -o /src/plugin.wasm -target wasip1 -buildmode=c-shared /src/plugin.go
```
Isso criará o arquivo binário `plugin.wasm` na raiz do diretório.

### 3. Empacotar o arquivo `.ndp`
Compacte o manifesto `manifest.json` e o binário `plugin.wasm` em formato zip sem caminhos de diretório adicionais (parâmetro `-j`):
```bash
zip -j spotify-sync.ndp manifest.json plugin.wasm
```

---

## 💻 Método 3: Compilação Local (Sem Docker)

Caso prefira instalar a toolchain de compilação diretamente no seu sistema operacional host (Ubuntu/Debian):

### 1. Instalar as dependências locais
```bash
# Instalar Go Compiler
sudo apt update && sudo apt install golang-go -y

# Instalar TinyGo (Exemplo via pacote Debian oficial)
wget https://github.com/tinygo-org/tinygo/releases/download/v0.31.2/tinygo_0.31.2_amd64.deb
sudo dpkg -i tinygo_0.31.2_amd64.deb
```

### 2. Resolver dependências e compilar
```bash
# Entrar no diretório do projeto
cd /home/isa7q/navidrome-plugin-spotify-sync

# Resolver dependências locais
go mod tidy

# Compilar para WebAssembly
tinygo build -o plugin.wasm -target wasip1 -buildmode=c-shared plugin.go

# Empacotar em .ndp
zip -j spotify-sync.ndp manifest.json plugin.wasm
```

---

## 📦 Gerenciamento de Versão e PDK em Go

O plugin faz uso do **Navidrome Plugin Development Kit (PDK)** oficial escrito em Go.
Ao atualizar o Navidrome para novas versões, pode ser necessário ajustar a pseudo-versão e o hash de commit do repositório PDK no seu arquivo [go.mod](file:///home/isa7q/navidrome-plugin-spotify-sync/go.mod).

### Como Consultar a Pseudo-Versão Atualizada do PDK:
1. Para descobrir qual é o timestamp e a pseudo-versão mais recente disponível no branch master do repositório do Navidrome, execute:
   ```bash
   go get github.com/navidrome/navidrome/plugins/pdk/go@master
   ```
2. O Go resolverá o commit e retornará no terminal algo semelhante a:
   ```text
   go: upgraded github.com/navidrome/navidrome/plugins/pdk/go v0.0.0-20260608122259-1b46b9771229
   ```
3. Copie essa string de versão para o seu arquivo `go.mod` sob a cláusula `require` para garantir a compatibilidade de compilação.
