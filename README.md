# prevs-comparation

Pipeline para download, processamento e comparação de previsões de **Energia Natural Afluente (ENA)** entre as fontes **ONS** e **TOK**.

## Visão geral

O pipeline executa as seguintes etapas:

1. **Download automático** dos arquivos de previsão:
   - ONS: baixa ZIP com `Prevs_VE.prv` via HTTP.
   - TOK: baixa pacote `.tar.gz` via `gsutil` a partir do Google Cloud Storage.
2. **Cálculo de ENA** por posto (usina), incluindo vazões artificiais, para cada fonte.
3. **Geração de comparativos** absolutos e relativos (TOK − ONS) por posto, bacia hidrográfica e subsistema elétrico.
4. **Geração de figuras** com tabelas comparativas para cada semana de previsão.

Os resultados são salvos em `data/output/<ano>/<mes>/`.

## Estrutura do projeto

```
main.py               # Ponto de entrada CLI
requirements.txt      # Dependências Python
setup.sh              # Script de criação do ambiente virtual
data/
  aux/                # Arquivos auxiliares fixos (produtibilidade, hidrograma, mapeamentos)
  input/
    ONS/              # Prevs_VE.prv extraído do ZIP
    TOK/              # Arquivo .rv2/.rv3 extraído do TAR
  output/             # CSVs e figuras gerados por rodada
downloads/
  ONS/                # Cache dos ZIPs baixados
  TOK/                # Cache dos TARs baixados
src/
  pipeline.py         # Orquestração completa do pipeline
  ena_processing.py   # Cálculo de ENA por posto e fonte
  comparisons.py      # Comparativos ABS/REL por posto, bacia e sistema
  figures.py          # Geração de figuras/tabelas comparativas
  io_utils.py         # Leitura/escrita de arquivos e caminhos padrão
```

## Requisitos

- Python 3.10+
- [`gsutil`](https://cloud.google.com/storage/docs/gsutil_install) instalado e autenticado
- Acesso ao Google Artifact Registry (para o pacote privado `tok-gcp-tools`)

## Instalação

```bash
bash setup.sh
source .env/bin/activate
```

O script cria um ambiente virtual em `.env`, instala os backends de autenticação do Google e todas as dependências listadas em `requirements.txt`.

## Uso

```bash
python main.py [ano] [mes] [revisao] [MODELO_base] [--root DIRETORIO]
```

| Argumento      | Descrição                                              | Exemplo                    |
|----------------|--------------------------------------------------------|----------------------------|
| `ano`          | Ano de processamento                                   | `2026`                     |
| `mes`          | Mês de processamento (1–12)                            | `5`                        |
| `revisao`      | Número da revisão do PMO                               | `3`                        |
| `MODELO_base`  | Modelo base para busca do arquivo TOK                  | `ETA40-GEFSav`             |
| `--root`       | Diretório raiz do projeto (padrão: diretório atual)    | `/caminho/para/o/projeto`  |

**Exemplo:**

```bash
python main.py 2026 5 3 ETA40-GEFSav
```

## Saídas

Todos os arquivos são salvos em `data/output/<ano>/<mes>/`:

| Arquivo                          | Descrição                                         |
|----------------------------------|---------------------------------------------------|
| `ena_ONS.csv`                    | ENA calculada por posto — fonte ONS               |
| `ena_TOK.csv`                    | ENA calculada por posto — fonte TOK               |
| `dif_abs_Posto_TOK-ONS.csv`      | Diferença absoluta por posto (TOK − ONS)          |
| `dif_abs_Bacia_TOK-ONS.csv`      | Diferença absoluta agregada por bacia             |
| `dif_abs_SISTEMA_TOK-ONS.csv`    | Diferença absoluta agregada por subsistema        |
| `dif_rel_Bacia_TOK-ONS.csv`      | Diferença relativa (%) por bacia                  |
| `dif_rel_SISTEMA_TOK-ONS.csv`    | Diferença relativa (%) por subsistema             |
| `figura_abs_*.png`               | Figura comparativa absoluta por semana            |
| `figura_rel_*.png`               | Figura comparativa relativa por semana            |
