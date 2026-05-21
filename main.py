from __future__ import annotations

"""Ponto de entrada do pipeline de ENA.

Este arquivo mantém apenas a interface de linha de comando,
delegando o processamento para módulos em `ena/`.
"""

import argparse
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Dtype inference on a pandas object",
    category=FutureWarning,
    module="pandas",
)

from src.pipeline import run_pipeline


def main(ano: int = 2026, mes: int = 5, revisao: int = 3, MODELO_base: str = "ETA40-GEFSav", root: Path = Path(".")) -> None:
    """Lê os argumentos CLI e dispara o pipeline completo."""
    parser = argparse.ArgumentParser(
        description=(
            "Executa pipeline completo ONS/TOK: cálculo de ENA, "
            "comparações ABS/REL e geração de figuras."
        )
    )
    parser.add_argument("ano", default=ano, nargs="?", const=ano, type=int, help="Ano de processamento (ex.: 2026)")
    parser.add_argument("mes", default=mes, nargs="?", const=mes, type=int, help="Mês de processamento (1-12, ex.: 5)")
    parser.add_argument("revisao", default=revisao, nargs="?", const=revisao, type=int, help="Revisão PMO (ex.: 3)")
    parser.add_argument("MODELO_base", default=MODELO_base, nargs="?", const=MODELO_base, type=str, help="Nome base do modelo para busca do TOK (ex: ETA40-GEFSav)")
    parser.add_argument("--root",
        default=root,
        help="Diretório raiz do projeto (default: diretório atual)",
    )
    args = parser.parse_args()

    if args.mes < 1 or args.mes > 12:
        raise ValueError("O mês deve estar entre 1 e 12.")

    run_pipeline(ano=args.ano, mes=args.mes, revisao=args.revisao, MODELO_base=args.MODELO_base, root=Path(args.root))

    print(args.ano, args.mes, args.revisao, args.MODELO_base, sep=", ")    

if __name__ == "__main__":
    main(revisao=2, MODELO_base="ECENSav-ETA40-GEFSav")
