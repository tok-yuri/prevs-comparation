"""
Constantes globais utilizadas no pipeline de cálculo de ENA.

Define a ordem canônica de exibição de bacias e sistemas nas figuras
comparativas geradas pelo pipeline.
"""

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
