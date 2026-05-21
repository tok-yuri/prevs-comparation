from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Ordem de exibição das bacias hidrográficas nas figuras e tabelas de saída.
# A sequência segue o padrão definido pelo ONS para apresentação dos resultados.
ORDEM_BACIA = [
    "Grande", "Paranaíba", "Tietê", "Paranapanema (SE)", "Paranapanema (S)",
    "Paranapanema total", "Alto Paraná", "Baixo Paraná", "Alto Tietê", "Paraíba do Sul",
    "Itabapoana", "Mucuri", "Santa Maria da Vitória", "Doce", "Paraguai", "Iguaçu",
    "Jacuí", "Uruguai", "Capivari", "Itajaí-Açu", "São Francisco (SE)", "São Francisco (NE)",
    "São Francisco total", "Parnaíba", "Paraguaçu", "Jequitinhonha (SE)", "Jequitinhonha (NE)",
    "Jequitinhonha total", "Tocantins (SE)", "Tocantins (N)", "Tocantins total",
    "Amazonas (SE)", "Amazonas (N)", "Amazonas total", "Araguari", "Xingu",
]

# Ordem de exibição dos subsistemas elétricos (regiões) nas figuras comparativas.
ORDEM_SISTEMA = ["SUDESTE", "SUL", "NORDESTE", "NORTE"]

def ordenar_bacias_sistemas(df_b: pd.DataFrame, df_s: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ordena bacias e sistemas com base na ordem canônica definida em constantes."""
    ord_b_map = {v: i for i, v in enumerate(ORDEM_BACIA)}
    df_b = (
        df_b.assign(_ord=df_b["Bacia"].map(ord_b_map).fillna(999))
        .sort_values(["_ord", "Bacia"])
        .drop(columns="_ord")
        .reset_index(drop=True)
    )

    ord_s_map = {v: i for i, v in enumerate(ORDEM_SISTEMA)}
    df_s = (
        df_s.assign(_ord=df_s["Bacia"].map(ord_s_map).fillna(999))
        .sort_values(["_ord", "Bacia"])
        .drop(columns="_ord")
        .reset_index(drop=True)
    )
    return df_b, df_s


def _gerar_figura_tabela(
    output_dir: Path,
    pmo_mes: str,
    pmo_revisao: int,
    arq_bacia: Path,
    arq_sistema: Path,
    rename_s: dict[str, str],
    formatador,
    output_name: str,
) -> None:
    """Função base para geração das figuras ABS/REL em formato de tabela colorida."""
    df_fig_bacia = pd.read_csv(arq_bacia)
    df_fig_sistema = pd.read_csv(arq_sistema)

    cols_s = ["S1", "S2", "S3", "S4", "S5", "S6"]
    df_b = df_fig_bacia.rename(columns=rename_s)[["BACIA"] + cols_s].rename(columns={"BACIA": "Bacia"})
    df_s = df_fig_sistema.rename(columns=rename_s)[["REGIAO"] + cols_s].rename(columns={"REGIAO": "Bacia"})

    # Padroniza nomes dos sistemas em caixa alta para casar com ORDEM_SISTEMA.
    df_s["Bacia"] = df_s["Bacia"].astype(str).str.upper()
    df_b, df_s = ordenar_bacias_sistemas(df_b, df_s)

    colunas = ["Bacia"] + cols_s
    linhas: list[list[str]] = []
    tipos: list[str] = []
    valores_plot: list[list[float]] = []

    # Bloco de bacias.
    for _, row in df_b.iterrows():
        linhas.append([row["Bacia"]] + [formatador(row[c]) for c in cols_s])
        valores_plot.append([row[c] for c in cols_s])
        tipos.append("bacia")

    # Linha separadora visual entre bacias e sistemas.
    linhas.append(["SISTEMA"] + cols_s)
    tipos.append("secao")

    # Bloco de sistemas.
    for _, row in df_s.iterrows():
        linhas.append([row["Bacia"]] + [formatador(row[c]) for c in cols_s])
        valores_plot.append([row[c] for c in cols_s])
        tipos.append("sistema")

    valores = np.array(valores_plot, dtype=float) if valores_plot else np.array([[0.0]])
    vmax = np.nanmax(np.abs(valores)) if valores.size else 1.0
    vmax = 1.0 if (not np.isfinite(vmax) or vmax == 0) else float(vmax + 0.3 * vmax)
    cmap = plt.cm.RdBu

    def cor_valor(v: float):
        if pd.isna(v) or abs(v) < 1e-12:
            return "#ffffff"
        t = (float(v) + vmax) / (2 * vmax)
        t = min(1.0, max(0.0, t))
        return cmap(t)

    header_color = "#93c47d"
    first_col_color = "#d9ead3"

    cell_text = [colunas] + linhas
    cell_colors = [[header_color] * len(colunas)]

    idx_valor = 0
    for tipo in tipos:
        if tipo == "secao":
            cell_colors.append([header_color] * len(colunas))
            continue

        row_colors = [first_col_color]
        for v in valores[idx_valor]:
            row_colors.append(cor_valor(v))
        cell_colors.append(row_colors)
        idx_valor += 1

    n_rows = len(cell_text)
    fig_h = max(8, n_rows * 0.38)
    fig, ax = plt.subplots(figsize=(10, fig_h))
    ax.axis("off")

    ax.set_title(
        f"Comparação de PREVS TOK-ONS\nPMO {pmo_mes} - Revisão {pmo_revisao}",
        fontsize=14,
        fontweight="bold",
        fontstyle="italic",
        pad=4,
    )

    tabela = ax.table(cellText=cell_text, cellColours=cell_colors, cellLoc="center", loc="upper center")
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(11)
    tabela.scale(1, 1.35)

    larguras = [0.34] + [0.11] * 6
    for c, w in enumerate(larguras):
        for r in range(n_rows):
            tabela[(r, c)].set_width(w)

    linha_secao = 1 + len(df_b)
    for (r, c), cell in tabela.get_celld().items():
        cell.set_edgecolor("#222222")
        cell.set_linewidth(0.8)
        cell.PAD = 0.015
        cell.get_text().set_va("center")

        if r == 0 or r == linha_secao:
            cell.set_text_props(weight="bold", va="center")

        if c == 0 and r > 0 and r != linha_secao:
            cell.set_text_props(weight="bold", ha="left", va="center")

    plt.tight_layout()
    plt.savefig(output_dir / output_name, dpi=300, bbox_inches="tight")
    plt.close(fig)


def gerar_figura_abs(output_dir: Path, pmo_mes: str, pmo_revisao: int, darq: str = "") -> None:
    """Gera figura com diferenças absolutas (TOK - ONS)."""

    def fmt_abs(x: float) -> str:
        if pd.isna(x):
            return ""
        return str(int(round(float(x))))

    _gerar_figura_tabela(
        output_dir=output_dir,
        pmo_mes=pmo_mes,
        pmo_revisao=pmo_revisao,
        arq_bacia=output_dir / "dif_abs_Bacia_TOK-ONS.csv",
        arq_sistema=output_dir / "dif_abs_SISTEMA_TOK-ONS.csv",
        rename_s={
            "ENA1_sDIF": "S1",
            "ENA2_sDIF": "S2",
            "ENA3_sDIF": "S3",
            "ENA4_sDIF": "S4",
            "ENA5_sDIF": "S5",
            "ENA6_sDIF": "S6",
        },
        formatador=fmt_abs,
        output_name=f"comp_abs_PREVS_TOK-ONS_{darq}.png" if darq else "comp_abs_PREVS_TOK-ONS.png",
    )


def gerar_figura_rel(output_dir: Path, pmo_mes: str, pmo_revisao: int, darq: str = "") -> None:
    """Gera figura com diferenças relativas (%) em relação ao ONS."""

    def fmt_rel(x: float) -> str:
        if pd.isna(x):
            return ""
        s = f"{float(x):.1f}"
        s = "0.0" if s == "-0.0" else s
        return f"{s}%"

    _gerar_figura_tabela(
        output_dir=output_dir,
        pmo_mes=pmo_mes,
        pmo_revisao=pmo_revisao,
        arq_bacia=output_dir / "dif_rel_Bacia_TOK-ONS.csv",
        arq_sistema=output_dir / "dif_rel_SISTEMA_TOK-ONS.csv",
        rename_s={
            "PERC1": "S1",
            "PERC2": "S2",
            "PERC3": "S3",
            "PERC4": "S4",
            "PERC5": "S5",
            "PERC6": "S6",
        },
        formatador=fmt_rel,
        output_name=f"comp_rel_PREVS_TOK-ONS_{darq}.png" if darq else "comp_rel_PREVS_TOK-ONS.png",
    )
