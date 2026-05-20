from __future__ import annotations

from datetime import date
from pathlib import Path
import subprocess
import tarfile
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve
import zipfile

from .comparisons import gerar_comparacoes
from .ena_processing import calcular_rev, processar_ena_fonte
from .figures import gerar_figura_abs, gerar_figura_rel
from .io_utils import PipelinePaths


def baixar_zip_ons_preliminar(root: Path, darq: str) -> Path:
    """Baixa o ZIP preliminar de vazões semanais ONS para o diretório vem-ONS."""
    base_url = (
        "https://storage.googleapis.com/tok_webhook/produtos_ons/"
        "resultados_preliminares_consistidos_vazoes_semanais_pmo/"
    )
    nome_arquivo = f"resultados_preliminares_consistidos_vazoes_semanais_pmo_{darq}.zip"
    url = f"{base_url}{nome_arquivo}"

    destino_dir = root / "vem-ONS"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino_arquivo = destino_dir / nome_arquivo

    if destino_arquivo.exists():
        print(f"[download ONS] Arquivo já existe: {destino_arquivo}")
        return destino_arquivo

    print(f"[download ONS] Baixando: {url}")
    try:
        urlretrieve(url, destino_arquivo)
    except HTTPError as exc:
        raise FileNotFoundError(
            f"Arquivo ONS não encontrado para darq={darq} (HTTP {exc.code}). URL: {url}"
        ) from exc
    except URLError as exc:
        raise ConnectionError(f"Falha de conexão ao baixar arquivo ONS: {url}") from exc

    print(f"[download ONS] Salvo em: {destino_arquivo}")
    return destino_arquivo


def extrair_prevs_ons(zip_path: Path, root: Path) -> tuple[Path, str]:
    """Extrai Consistido/Prevs_VE.prv do ZIP e copia para data/input/ONS.

    Retorna o caminho do arquivo extraído e a data de criação do arquivo
    dentro do ZIP no formato aaaammdd.
    """
    destino = root / "data" / "input" / "ONS" / "Prevs_VE.prv"
    destino.parent.mkdir(parents=True, exist_ok=True)

    alvo = "Consistido/Prevs_VE.prv"
    membro_encontrado: str | None = None
    darq_tok: str = ""

    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            nome_normalizado = info.filename.replace("\\", "/")
            if nome_normalizado.endswith(alvo):
                membro_encontrado = info.filename
                ano_arq, mes_arq, dia_arq = info.date_time[:3]
                darq_tok = f"{ano_arq:04d}{mes_arq:02d}{dia_arq:02d}"
                break

        if membro_encontrado is None:
            raise FileNotFoundError(f"Arquivo {alvo} não encontrado dentro de {zip_path}")

        with zf.open(membro_encontrado) as origem, destino.open("wb") as saida:
            saida.write(origem.read())

    print(f"[download ONS] Copiado para: {destino}")
    print(f"[download ONS] Data do Prevs_VE.prv no ZIP (darq_tok): {darq_tok}")
    return destino, darq_tok


def baixar_tar_tok_gsutil(paths: PipelinePaths, ano: int, mes: int, darq: str, MODELO_base: str) -> Path:
    """Baixa o pacote PREVS TOK via gsutil para o diretório vem-TOK, usando MODELO_base."""
    periodo = f'{darq[:4]}-{darq[4:6]}'
    nome_tar = f"PREVS_{MODELO_base}-ECENS45-av_upt_{darq}.tar.gz"
    origem_gs = (
        f"gs://storage.tempook.com/Comercializadora/Arquivos/PREVS/"
        f"{MODELO_base}-ECENS45_upt/{MODELO_base}-ECENS45-av_upt/"
        f"{periodo}/{nome_tar}"
    )

    destino_dir = paths.root / "vem-TOK"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino_tar = destino_dir / nome_tar

    if destino_tar.exists():
        print(f"[download TOK] Arquivo já existe: {destino_tar}")
        return destino_tar

    print(f"[download TOK] Baixando com gsutil: {origem_gs}")
    try:
        subprocess.run(
            ["gsutil", "-m", "cp", origem_gs, "."],
            check=True,
            text=True,
            capture_output=True,
            cwd=destino_dir,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Comando gsutil não encontrado. Instale/configure o gsutil para baixar o arquivo TOK."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise FileNotFoundError(
            "Falha ao baixar arquivo TOK via gsutil para "
            f"ano={ano}, mes={mes}, darq={darq}. Erro: {stderr}"
        ) from exc

    print(f"[download TOK] Salvo em: {destino_tar}")
    return destino_tar


def extrair_tok_revisao_do_tar(
    tar_path: Path, paths: PipelinePaths, ano: int, mes: int, revisao: int
) -> Path:
    """Extrai do .tar.gz o arquivo TOK compatível com ano/mês/revisão."""
    paths.tok_input_dir.mkdir(parents=True, exist_ok=True)
    alvo: tuple[str, bytes] | None = None

    with tarfile.open(tar_path, "r:gz") as tf:
        for membro in tf.getmembers():
            if not membro.isfile():
                continue

            nome = Path(membro.name).name
            nome_lower = nome.lower()
            if (
                "prevs" in nome_lower
                and f"_{ano}_{mes:02d}_" in nome
                and nome.endswith(f".rv{revisao}")
            ):
                arquivo = tf.extractfile(membro)
                if arquivo is None:
                    continue
                alvo = (nome, arquivo.read())
                break

    if alvo is None:
        raise FileNotFoundError(
            f"Não encontrei no tar {tar_path.name} um arquivo TOK para "
            f"ano={ano}, mes={mes}, revisao={revisao}."
        )

    nome_alvo, dados = alvo
    destino = paths.tok_input_dir / nome_alvo
    with destino.open("wb") as saida:
        saida.write(dados)

    print(f"[download TOK] Arquivo da revisão copiado para: {destino}")
    return destino


def localizar_arquivo_tok(
    paths: PipelinePaths,
    ano: int,
    mes: int,
    revisao: int,
    darq_tok: str = "",
    darq: str = "",
    MODELO_base: str = "ETA40-GEFSav",
) -> Path:
    """Localiza automaticamente o arquivo variável TOK para ano/mês/revisão."""
    candidatos: list[Path] = []
    padroes = [
        f"{darq_tok}_*_{ano}_{mes:02d}_*rv{revisao}" if darq_tok else f"*_{ano}_{mes:02d}_*rv{revisao}",
        f"*prevs*_{ano}_{mes:02d}_*rv{revisao}",
    ]

    # 1) Primeiro tenta o diretório oficial de entrada variável.
    for padrao in padroes:
        candidatos.extend(sorted(paths.tok_input_dir.glob(padrao)))

    # 2) Fallback para histórico bruto de origem (manter compatibilidade operacional).
    if not candidatos:
        for padrao in padroes:
            candidatos.extend(sorted((paths.root / "vem-TOK").rglob(padrao)))

    # 3) Se não encontrou localmente, baixa via gsutil e extrai a revisão desejada.
    if not candidatos and darq_tok:
        tar_path = baixar_tar_tok_gsutil(paths, ano, mes, darq=darq_tok, MODELO_base=MODELO_base)
        return extrair_tok_revisao_do_tar(tar_path, paths, ano, mes, revisao)

    if not candidatos:
        raise FileNotFoundError(
            f"Não encontrei arquivo TOK para ano={ano}, mes={mes}, revisao={revisao}."
        )

    candidatos = sorted(candidatos, key=lambda p: (len(str(p)), str(p)))
    return candidatos[0]


def run_pipeline(ano: int, mes: int, revisao: int, MODELO_base: str = "ETA40-GEFSav", root: Path = Path(".")) -> None:
    """Executa o pipeline completo ONS/TOK de ENA, comparações e figuras."""
    data_ref = calcular_rev(ano, mes, revisao)
    print(f"[0/5] Data de referência da revisão {revisao}: {data_ref}")
    darq = data_ref.strftime("%Y%m%d")
    print(f"darq: {darq}")
    zip_ons = baixar_zip_ons_preliminar(root, darq)
    _, darq_tok = extrair_prevs_ons(zip_ons, root)
    print("[download ONS] Download, descompactação e cópia do Prevs_VE.prv concluídos.")

    paths = PipelinePaths.from_root(root)
    outdir = paths.output_run_dir(ano=ano, mes=mes, revisao=revisao)
    outdir.mkdir(parents=True, exist_ok=True)

    prevs_ons = paths.ons_prevs
    prevs_tok = localizar_arquivo_tok(paths, ano, mes, revisao, darq_tok=darq_tok, darq=darq, MODELO_base=MODELO_base)

    print(f"[1/5] Calculando ENA ONS ({prevs_ons})")
    processar_ena_fonte(
        prevs_prv=prevs_ons,
        hidro_b=paths.hidro_b,
        prod_file=paths.prod,
        bacia_regiao=paths.bacia_regiao,
        ano_inicio=ano,
        mes_inicio=mes,
        outdir=outdir,
        output_suffix="ONS",
    )

    print(f"[2/5] Calculando ENA TOK ({prevs_tok})")
    processar_ena_fonte(
        prevs_prv=prevs_tok,
        hidro_b=paths.hidro_b,
        prod_file=paths.prod,
        bacia_regiao=paths.bacia_regiao,
        ano_inicio=ano,
        mes_inicio=mes,
        outdir=outdir,
        output_suffix="TOK",
    )

    print("[3/5] Gerando comparações absoluta e relativa (.csv)")
    gerar_comparacoes(
        outdir,
        ons_limpo=outdir / "ONS_total_limpa.csv",
        tok_limpo=outdir / "TOK_total_limpa.csv",
    )

    pmo_mes = date(ano, mes, 1).strftime("%b")

    print("[4/5] Gerando figura absoluta")
    gerar_figura_abs(outdir, pmo_mes=pmo_mes, pmo_revisao=revisao, darq=darq)

    print("[5/5] Gerando figura relativa")
    gerar_figura_rel(outdir, pmo_mes=pmo_mes, pmo_revisao=revisao, darq=darq)

    print("\nPipeline concluído com sucesso.")
    print(f"Saídas da rodada: {outdir}")
