from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


def to_posto_wide(df: pd.DataFrame, posto_col: str) -> pd.DataFrame:
    """Converte um DataFrame no formato longo para formato largo por posto.

    O comportamento esperado é:
    - definir a coluna `posto_col` como índice;
    - transpor o DataFrame para que as semanas/atributos fiquem em linhas;
    - normalizar códigos de posto para 3 dígitos (ex.: 1 -> 001).
    """
    if "Index" in df.columns:
        df = df.drop(columns=["Index"])

    df = df.set_index(posto_col)
    df.index = df.index.astype(str)

    df_t = df.T
    df_t.columns = df_t.columns.astype(str).str.zfill(3)
    return df_t


def adicionar_bacias_total(
    df_bacia: pd.DataFrame,
    nome_coluna: str,
    cols_valor: Iterable[str],
) -> pd.DataFrame:
    """Adiciona linhas de bacias totais a partir da soma de pares de bacias.

    A função preserva a ordem original do DataFrame e insere cada total
    logo após as linhas de origem.
    """
    regras_totais = [
        ("Amazonas total", ["Amazonas (N)", "Amazonas (SE)"]),
        ("Jequitinhonha total", ["Jequitinhonha (NE)", "Jequitinhonha (SE)"]),
        ("Paranapanema total", ["Paranapanema (S)", "Paranapanema (SE)"]),
        ("São Francisco total", ["São Francisco (NE)", "São Francisco (SE)"]),
        ("Tocantins total", ["Tocantins (NE)", "Tocantins (SE)"]),
    ]

    out = df_bacia.copy()
    for nome_total, origens in regras_totais:
        # Compatibilidade para bases que usam "Tocantins (N)" em vez de "(NE)".
        origens_ajustadas = origens.copy()
        if "Tocantins (NE)" in origens_ajustadas and "Tocantins (NE)" not in set(out[nome_coluna]):
            if "Tocantins (N)" in set(out[nome_coluna]):
                origens_ajustadas = ["Tocantins (N)", "Tocantins (SE)"]

        bloco = out[out[nome_coluna].isin(origens_ajustadas)]
        if len(bloco) != 2:
            continue

        nova = {nome_coluna: nome_total}
        if "REGIAO" in out.columns:
            nova["REGIAO"] = "Total"

        for c in cols_valor:
            nova[c] = bloco[c].sum()

        linha_total = pd.DataFrame([nova])
        idx_insercao = out[out[nome_coluna].isin(origens_ajustadas)].index.max() + 1
        out = pd.concat([out.iloc[:idx_insercao], linha_total, out.iloc[idx_insercao:]], ignore_index=True)

    return out


@dataclass(frozen=True)
class PipelinePaths:
    """Caminhos padrão de entrada e saída do pipeline.

    Convenção usada:
    - `data/input`: arquivos variáveis por rodada (ONS/TOK);
    - `data/aux`: arquivos fixos de apoio (produtibilidade, hidrograma, mapeamentos);
    - `data/output`: resultados gerados.
    """

    root: Path
    input_dir: Path
    aux_dir: Path
    output_base_dir: Path
    ons_prevs: Path
    tok_input_dir: Path
    hidro_b: Path
    prod: Path
    bacia_regiao: Path

    @classmethod
    def from_root(cls, root: Path) -> "PipelinePaths":
        data_dir = root / "data"
        input_dir = data_dir / "input"
        aux_dir = data_dir / "aux"
        output_base_dir = data_dir / "output"

        return cls(
            root=root,
            input_dir=input_dir,
            aux_dir=aux_dir,
            output_base_dir=output_base_dir,
            ons_prevs=input_dir / "ONS" / "Prevs_VE.prv",
            tok_input_dir=input_dir / "TOK",
            hidro_b=aux_dir / "Hidro_B.csv",
            prod=aux_dir / "Prod.csv",
            bacia_regiao=aux_dir / "bacia_regiao.csv",
        )

    def output_run_dir(self, ano: int, mes: int, revisao: int) -> Path:
        """Retorna o diretório de saída da rodada no formato output/ano/mes/rev."""
        return self.output_base_dir / str(ano) / f"{mes:02d}" / f"rev{revisao}"
