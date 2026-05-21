from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .io_utils import to_posto_wide


def add_vazoes_artificiais(naturais: pd.DataFrame) -> pd.DataFrame:
    """Calcula vazões artificiais a partir das vazões naturais por posto."""
    art = pd.DataFrame(index=naturais.index)

    # TIETÊ
    dif = 0.1 * (naturais["161"].copy() - naturais["117"].copy() - naturais["118"].copy()) + naturais["117"].copy() + naturais["118"].copy()
    art["319"] = dif
    art["037"] = naturais["237"].copy() - dif
    art["038"] = naturais["238"].copy() - dif
    art["039"] = naturais["239"].copy() - dif
    art["040"] = naturais["240"].copy() - dif
    art["042"] = naturais["242"].copy() - dif
    art["043"] = naturais["243"].copy() - dif

    # PARANÁ
    art["044"] = naturais["244"].copy() - dif
    art["045"] = naturais["245"].copy() - dif
    art["046"] = naturais["246"].copy() - dif
    art["066"] = naturais["266"].copy() - dif

    # HENRY BORDEN
    art["318"] = naturais["116"].copy() + dif

    # IGUAÇU
    art["075"] = naturais["076"].copy() + naturais["073"].apply(lambda x: min(x - 10, 173.5))

    # JACUÍ
    art["221"] = naturais["224"].copy()

    # PARAGUAI
    art["252"] = naturais["259"].copy()

    # PARAÍBA DO SUL
    vaz_125 = naturais["125"].astype(float).to_numpy(copy=True)
    cond1 = vaz_125 <= 190
    cond2 = (vaz_125 > 190) & (vaz_125 <= 209)
    cond3 = (vaz_125 > 209) & (vaz_125 <= 250)
    cond4 = vaz_125 > 250

    vaz_298 = vaz_125.copy()
    vaz_298[cond1] = vaz_125[cond1] * 119 / 190
    vaz_298[cond2] = 119
    vaz_298[cond3] = vaz_125[cond3] - 90
    vaz_298[cond4] = 160

    art["298"] = vaz_298
    art["132"] = naturais["202"].values + np.minimum(naturais["201"].values, np.full(len(naturais), 25))
    art["317"] = np.maximum(naturais["201"].values - 25, np.zeros(len(naturais)))
    art.loc[:, "315"] = (naturais["203"].copy() - naturais["201"].copy()).values + art["317"] + art["298"]
    art["316"] = np.minimum(art["315"].values, np.full(len(naturais), 190))
    art.loc[:, "304"] = art["315"] - art["316"]
    art.loc[:, "127"] = naturais["129"].copy() - art["298"] - naturais["203"].copy() + art["304"]
    art["126"] = np.where(art["127"].values <= 430, np.maximum(0, art["127"].values - 90), 340)
    art.loc[:, "299"] = naturais["130"].copy() - art["298"] - naturais["203"].copy() + art["304"].copy() - art["126"].copy()
    art["131"] = np.minimum(art["316"].values, np.full(len(naturais), 144))
    art["303"] = np.where(art["132"].values < 17, art["132"].values, 17) + np.minimum(
        art["316"].values - art["131"].values,
        np.full(len(naturais), 34),
    )
    art.loc[:, "306"] = art["303"] + art["131"]

    # OUTRAS SUDESTE
    art.loc[:, "166"] = naturais["266"].copy() - naturais["244"].copy() - naturais["061"].copy()
    art["366"] = naturais["266"].copy()

    result = pd.concat([naturais, art], axis="columns")
    result.columns = result.columns.astype(object)
    return result


def calcular_data(ano_inicio: int, mes_inicio: int) -> date:
    """Retorna a data de referência (domingo anterior ao 1º dia do mês)."""
    primeiro_dia = date(ano_inicio, mes_inicio, 1)
    weekday_excel = 0 if primeiro_dia.isoweekday() % 7 == 6 else primeiro_dia.isoweekday() % 7 + 1
    return primeiro_dia - timedelta(days=weekday_excel)

def calcular_rev(ano_inicio: int, mes_inicio: int, rev: int = 0) -> date:
    dzero = calcular_data(ano_inicio, mes_inicio)
    print("dzero", dzero)
    print(dzero + timedelta(days=rev * 7))
    return dzero + timedelta(days=rev * 7) 
    
def calcular_e_inserir_vazao_belo_monte(
    art_df: pd.DataFrame,
    hidrograma: pd.DataFrame,
    data_inicio: date,
) -> pd.DataFrame:
    """Calcula e adiciona vazões dos postos 292 e 302 a partir de 288 e HidroB."""
    semanas = [f"S{i}" for i in range(1, 7)]
    datas = pd.date_range(start=pd.Timestamp(data_inicio), periods=42, freq="D")
    semana_ref = [semanas[i // 7] for i in range(42)]

    if "288" not in art_df.columns:
        raise KeyError("Coluna do posto '288' não encontrada no DataFrame de vazões.")

    posto_288 = np.array([art_df.loc[s, "288"] for s in semana_ref], dtype=float)

    hidro = hidrograma.copy()
    hidro.loc[:, "MDA"] = pd.to_datetime(hidro["MDA"])
    hidro = hidro.set_index("MDA").sort_index()

    hidro_b = hidro.reindex(datas)["HidroB"]
    if hidro_b.isna().any():
        faltantes = datas[hidro_b.isna()]
        raise ValueError(f"HidroB ausente para datas: {[d.strftime('%Y-%m-%d') for d in faltantes]}")
    hidro_b = hidro_b.to_numpy(dtype=float)

    vaz_292 = np.where(posto_288 < hidro_b, 0, np.where(posto_288 > (hidro_b + 13900), 13900, posto_288 - hidro_b))

    df_diario = pd.DataFrame({"semana": semana_ref, "vaz_288": posto_288, "vaz_292": vaz_292})
    vaz_292_semanal = df_diario.groupby("semana")["vaz_292"].mean()
    vaz_288_semanal = df_diario.groupby("semana")["vaz_288"].mean()
    vaz_302_semanal = vaz_288_semanal - vaz_292_semanal

    out = art_df.copy()
    out["292"] = vaz_292_semanal.values
    out["302"] = vaz_302_semanal.values
    out = out.sort_index(axis=1)
    return out


def processar_ena_fonte(
    prevs_prv: Path,
    hidro_b: Path,
    prod_file: Path,
    bacia_regiao: Path,
    ano_inicio: int,
    mes_inicio: int,
    outdir: Path,
    output_suffix: str,
    input_encoding: str = "latin1",
    output_encoding: str = "latin1",
) -> None:
    """Processa uma fonte (ONS ou TOK) e gera todos os CSVs de saída da fonte."""
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Leitura de vazões naturais no formato semanal por posto.
    data = pd.read_csv(prevs_prv, sep=r"\s+", header=None)
    data.columns = ["Index", "Posto", "S1", "S2", "S3", "S4", "S5", "S6"]
    data_t = to_posto_wide(data, "Posto")

    # 2) Cálculo de vazões artificiais (inclui complementos hidráulicos específicos).
    art_df = add_vazoes_artificiais(data_t)

    # 3) Cálculo de Xingu/Belo Monte com hidrograma diário.
    hidrograma = pd.read_csv(hidro_b, encoding=input_encoding, parse_dates=["MDA"], dayfirst=True)
    data_inicio = calcular_data(ano_inicio, mes_inicio)
    art_df = calcular_e_inserir_vazao_belo_monte(art_df, hidrograma, data_inicio)

    # 4) Identificação NAT/ART e geração do arquivo base de vazões.
    cols_apenas_art_df = sorted(set(art_df.columns) - set(data_t.columns))
    identifica_posto = pd.DataFrame(
        [["ART" if col in cols_apenas_art_df else "NAT" for col in art_df.columns]],
        columns=art_df.columns,
        index=["Tipo"],
    )

    saida_df = pd.concat([identifica_posto, art_df], axis=0)
    cols_ordenadas = sorted(saida_df.columns, key=lambda x: int(x))
    saida_df = saida_df.loc[:, cols_ordenadas]

    # 5) ENA por posto usando produtibilidade fixa (arquivo auxiliar em data/aux).
    prod_df = pd.read_csv(prod_file, encoding=input_encoding)
    prod_t = to_posto_wide(prod_df, "POSTO")
    produtibilidade = pd.to_numeric(prod_t.loc["PRODUTIBILIDADE"], errors="coerce")
    produtibilidade.index = pd.Index(produtibilidade.index.astype(str).str.zfill(3), dtype=object)
    produtibilidade = produtibilidade.groupby(level=0).first()

    fatores = produtibilidade.reindex(art_df.columns)
    art_df_prod = art_df.mul(fatores, axis=1)
    art_df_prod.index = art_df_prod.index.str.replace("S", "ENA", regex=False)

    # 6) Consolidação das informações auxiliares para o arquivo completo por posto.
    art_df_prod_unico = art_df_prod.loc[:, ~art_df_prod.columns.duplicated(keep="last")]
    art_df_unico = art_df.loc[:, ~art_df.columns.duplicated(keep="last")]
    identifica_unico = identifica_posto.loc[:, ~identifica_posto.columns.duplicated(keep="last")]
    prod_t_unico = prod_t.loc[:, ~prod_t.columns.duplicated(keep="first")]

    cols_union = art_df_prod_unico.columns.union(prod_t_unico.columns)
    df3 = pd.concat(
        [
            prod_t_unico.reindex(columns=cols_union),
            identifica_unico.reindex(columns=cols_union),
            art_df_unico.reindex(columns=cols_union),
            art_df_prod_unico.reindex(columns=cols_union),
        ],
        axis=0,
    )
    df3.T.to_csv(outdir / f"{output_suffix}_vazoes_ENAs.csv", encoding=output_encoding, index=True, sep=";")

    # 7) Junção com mapeamento de bacia/região e gravação da saída total.
    bacia_regiao_df = pd.read_csv(bacia_regiao, encoding=input_encoding)
    bacia_regiao_t = to_posto_wide(bacia_regiao_df, "POSTO")
    bacia_regiao_t_unico = bacia_regiao_t.loc[:, ~bacia_regiao_t.columns.duplicated(keep="first")]

    cols_union_2 = df3.columns.union(bacia_regiao_t_unico.columns)
    df4 = pd.concat(
        [
            df3.reindex(columns=cols_union_2),
            bacia_regiao_t_unico.reindex(columns=cols_union_2),
        ],
        axis=0,
    )

    saida_total = df4.T
    saida_total.index.name = "Posto"
    saida_total.to_csv(outdir / f"{output_suffix}_total.csv", encoding=output_encoding, index=True)
    saida_total.dropna().to_csv(outdir / f"{output_suffix}_total_limpa.csv", encoding=output_encoding, index=True)

    # 8) Agregação de ENA por bacia.
    mapa_bacia = bacia_regiao_t.loc["BACIA"].copy()
    mapa_bacia.index = pd.Index(mapa_bacia.index.astype(str).str.zfill(3), dtype=object)
    mapa_bacia = mapa_bacia[~mapa_bacia.index.duplicated(keep="first")]

    ena_df = art_df_prod.copy()
    ena_df.columns = pd.Index(ena_df.columns.astype(str).str.zfill(3), dtype=object)
    ena_df = ena_df.loc[:, ~ena_df.columns.duplicated(keep="last")]
    ena_df = ena_df.apply(pd.to_numeric, errors="coerce")

    postos_comuns = ena_df.columns.intersection(mapa_bacia.index)
    bacias_alinhadas = mapa_bacia.loc[postos_comuns]
    mask_validos = bacias_alinhadas.notna()

    ena_df_bacia = ena_df.loc[:, postos_comuns[mask_validos]]
    bacias_alinhadas = bacias_alinhadas[mask_validos]

    ena_por_bacia = ena_df_bacia.T.groupby(bacias_alinhadas).sum(min_count=1).T
    ena_por_bacia = ena_por_bacia.reindex(sorted(ena_por_bacia.columns), axis=1)
    ena_por_bacia.T.to_csv(outdir / f"{output_suffix}_ena_por_bacia.csv", encoding=output_encoding, index=True)

    # 9) Agregação de ENA por subsistema (região).
    linha_regiao = "REGIÃO" if "REGIÃO" in bacia_regiao_t.index else "REGIAO"
    mapa_regiao = bacia_regiao_t.loc[linha_regiao].copy()
    mapa_regiao.index = pd.Index(mapa_regiao.index.astype(str).str.zfill(3), dtype=object)
    mapa_regiao = mapa_regiao[~mapa_regiao.index.duplicated(keep="first")]

    postos_comuns_regiao = ena_df.columns.intersection(mapa_regiao.index)
    regioes_alinhadas = mapa_regiao.loc[postos_comuns_regiao]
    mask_validos_regiao = regioes_alinhadas.notna()

    ena_df_reg = ena_df.loc[:, postos_comuns_regiao[mask_validos_regiao]]
    regioes_alinhadas = regioes_alinhadas[mask_validos_regiao]

    ena_por_regiao = ena_df_reg.T.groupby(regioes_alinhadas).sum(min_count=1).T
    ena_por_regiao = ena_por_regiao.reindex(sorted(ena_por_regiao.columns), axis=1)
    ena_por_regiao.T.to_csv(outdir / f"{output_suffix}_ena_por_regiao.csv", encoding=output_encoding, index=True)
