from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import adicionar_bacias_total


def gerar_comparacoes(output_dir: Path, ons_limpo: Path, tok_limpo: Path) -> None:
    """Gera comparativos absolutos e relativos entre as saídas TOK e ONS."""
    output_dir.mkdir(parents=True, exist_ok=True)

    df_ons = pd.read_csv(ons_limpo)
    df_tok = pd.read_csv(tok_limpo)

    cols_ena = [f"ENA{i}" for i in range(1, 7)]

    # ABS por posto: diferença direta TOK - ONS para cada semana ENA.
    base_cols = ["Posto", "NOME", "Tipo", "BACIA", "REGIAO", "PRODUTIBILIDADE"]
    tok_ena = df_tok[base_cols + cols_ena].copy().rename(columns={c: f"{c}_TOK" for c in cols_ena})
    ons_ena = df_ons[["Posto"] + cols_ena].copy().rename(columns={c: f"{c}_ONS" for c in cols_ena})

    df_dif_abs = tok_ena.merge(ons_ena, on="Posto", how="inner")
    for i in range(1, 7):
        df_dif_abs.loc[:, f"ENA{i}_DIF"] = df_dif_abs[f"ENA{i}_TOK"] - df_dif_abs[f"ENA{i}_ONS"]

    cols_finais = [
        "Posto",
        "NOME",
        "Tipo",
        "BACIA",
        "REGIAO",
        "PRODUTIBILIDADE",
        "ENA1_DIF",
        "ENA2_DIF",
        "ENA3_DIF",
        "ENA4_DIF",
        "ENA5_DIF",
        "ENA6_DIF",
    ]
    df_dif_abs = df_dif_abs[cols_finais]
    df_dif_abs.to_csv(output_dir / "dif_abs_Posto_TOK-ONS.csv", index=False, encoding="utf-8")

    # ABS por bacia: soma das diferenças por bacia/região.
    cols_dif = [f"ENA{i}_DIF" for i in range(1, 7)]
    cols_sdif = [f"ENA{i}_sDIF" for i in range(1, 7)]
    rename_sdif = dict(zip(cols_dif, cols_sdif))

    df_dif_bacia = (
        df_dif_abs.groupby(["BACIA", "REGIAO"], as_index=False)[cols_dif]
        .sum()
        .rename(columns=rename_sdif)
    )
    df_dif_bacia = adicionar_bacias_total(df_dif_bacia, "BACIA", cols_sdif)
    df_dif_bacia = df_dif_bacia[["BACIA", "REGIAO"] + cols_sdif]
    df_dif_bacia.to_csv(output_dir / "dif_abs_Bacia_TOK-ONS.csv", index=False, encoding="utf-8")

    # ABS por sistema: soma das diferenças por região.
    df_dif_sistema = (
        df_dif_abs.groupby("REGIAO", as_index=False)[cols_dif]
        .sum()
        .rename(columns=rename_sdif)
    )
    df_dif_sistema = df_dif_sistema[["REGIAO"] + cols_sdif]
    df_dif_sistema.to_csv(output_dir / "dif_abs_SISTEMA_TOK-ONS.csv", index=False, encoding="utf-8")

    # REL por bacia: percentual em relação à ENA ONS agregada.
    df_ons_bacia = df_ons.groupby("BACIA", as_index=False)[cols_ena].sum()
    df_ons_bacia = adicionar_bacias_total(df_ons_bacia, "BACIA", cols_ena)

    dif_abs_bacia = pd.read_csv(output_dir / "dif_abs_Bacia_TOK-ONS.csv")
    dif_abs_bacia.columns = ["BACIA", "REGIAO", "DIF1", "DIF2", "DIF3", "DIF4", "DIF5", "DIF6"]

    dif_perc_bacia = dif_abs_bacia.merge(df_ons_bacia[["BACIA"] + cols_ena], on="BACIA", how="inner")
    for i in range(1, 7):
        dif_perc_bacia.loc[:, f"PERC{i}"] = np.where(
            dif_perc_bacia[f"ENA{i}"] != 0,
            (dif_perc_bacia[f"DIF{i}"] / dif_perc_bacia[f"ENA{i}"]) * 100,
            np.nan,
        )

    df_perc_bacia = dif_perc_bacia[["BACIA", "REGIAO"] + [f"PERC{i}" for i in range(1, 7)]].copy()
    df_perc_bacia = df_perc_bacia.drop_duplicates(subset="BACIA")
    df_perc_bacia.to_csv(output_dir / "dif_rel_Bacia_TOK-ONS.csv", index=False)

    # REL por sistema: percentual da diferença regional sobre ENA regional ONS.
    cols_dif_rel = [f"DIF{i}" for i in range(1, 7)]
    df_ons_regiao = df_ons.groupby("REGIAO", as_index=False)[cols_ena].sum()

    dif_abs_regiao = (
        dif_abs_bacia[dif_abs_bacia["REGIAO"] != "Total"]
        .groupby("REGIAO", as_index=False)[cols_dif_rel]
        .sum()
    )

    dif_perc_regiao = dif_abs_regiao.merge(df_ons_regiao, on="REGIAO", how="inner")
    for i in range(1, 7):
        dif_perc_regiao.loc[:, f"PERC{i}"] = np.where(
            dif_perc_regiao[f"ENA{i}"] != 0,
            (dif_perc_regiao[f"DIF{i}"] / dif_perc_regiao[f"ENA{i}"]) * 100,
            np.nan,
        )

    df_perc_regiao = dif_perc_regiao[["REGIAO"] + [f"PERC{i}" for i in range(1, 7)]].copy()
    df_perc_regiao.to_csv(output_dir / "dif_rel_SISTEMA_TOK-ONS.csv", index=False)
