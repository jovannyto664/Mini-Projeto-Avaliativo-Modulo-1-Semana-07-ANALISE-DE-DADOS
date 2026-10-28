"""Análise exploratória da base Varejo para o mini-projeto."""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd


COLUNAS_CATEGORIA = ("PR_CAT", "CATEGORIA", "CATEGORY")
COLUNAS_GENERO = ("CL_GENERO", "GENERO", "GENDER", "SEXO")
COLUNAS_COMPRA = ("CO_ID", "ID_COMPRA", "COMPRA_ID", "ORDER_ID")
COLUNAS_CLIENTE = ("CL_ID", "ID_CLIENTE", "CLIENTE_ID", "CUSTOMER_ID")
COLUNAS_FILHOS = (
    "CL_FHL",
    "NUMERO_FILHOS",
    "NUMERO_DE_FILHOS",
    "FILHOS",
    "CHILDREN",
)
COLUNAS_DATA = ("DATA", "DATA_COMPRA", "DATE", "ORDER_DATE")
COLUNAS_DIMENSOES = (
    "ALTURA",
    "LARGURA",
    "COMPRIMENTO",
    "PROFUNDIDADE",
    "PESO",
    "DIMENSAO",
    "DIMENSOES",
)


def normalizar_nome(nome: object) -> str:
    """Padroniza nomes para localizar colunas apesar de acentos e espaços."""
    texto = unicodedata.normalize("NFKD", str(nome))
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return re.sub(r"[^A-Z0-9]+", "_", texto.upper()).strip("_")


def localizar_coluna(
    colunas: pd.Index, alternativas: tuple[str, ...]
) -> str | None:
    nomes = {normalizar_nome(coluna): str(coluna) for coluna in colunas}
    for alternativa in alternativas:
        if normalizar_nome(alternativa) in nomes:
            return nomes[normalizar_nome(alternativa)]
    return None


def carregar_base(caminho: Path) -> pd.DataFrame:
    """Lê a base publicada no Kaggle, usando a codificação e separador observados."""
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}. Baixe o CSV indicado no README."
        )

    # O arquivo do Kaggle usa ponto e vírgula e codificação compatível com Latin-1.
    df = pd.read_csv(caminho, sep=";", encoding="latin1", low_memory=False)
    df.columns = [str(coluna).strip() for coluna in df.columns]
    # Células contendo apenas espaços também são valores ausentes.
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    return df


def relatar_qualidade(df: pd.DataFrame) -> int:
    # Exibe o perfil da fonte antes de qualquer transformação.
    print(f"Registros carregados: {len(df):,}".replace(",", "."))
    print(f"Colunas carregadas: {len(df.columns)}")
    print("\nTipos de dados originais:")
    print(df.dtypes.to_string())
    print("\nValores ausentes por coluna:")
    print(df.isna().sum().to_string())

    duplicatas = int(df.duplicated().sum())
    print(f"\nLinhas totalmente duplicadas: {duplicatas:,}".replace(",", "."))
    categoria = localizar_coluna(df.columns, COLUNAS_CATEGORIA)
    if categoria:
        marcadores_categoria = df[categoria].astype("string").str.strip().str.upper().isin(
            {"#N/D", "N/D"}
        )
        print(
            "Categorias marcadas como não disponíveis (#N/D ou N/D): "
            f"{int(marcadores_categoria.sum()):,}".replace(",", ".")
        )
    return duplicatas


def limpar_base(df_original: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    df = df_original.copy()
    relatorio: dict[str, object] = {}

    # Remove somente colunas excedentes que não possuem nenhum dado.
    colunas_vazias = [
        coluna
        for coluna in df.columns
        if normalizar_nome(coluna).startswith("UNNAMED")
        or normalizar_nome(coluna) == ""
    ]
    colunas_vazias = [coluna for coluna in colunas_vazias if df[coluna].isna().all()]
    if colunas_vazias:
        df = df.drop(columns=colunas_vazias)
    relatorio["colunas_vazias_removidas"] = len(colunas_vazias)

    # O arquivo usa #N/D para categorias desconhecidas; padronize junto com nulos.
    categoria = localizar_coluna(df.columns, COLUNAS_CATEGORIA)
    if categoria:
        marcador_ausente = df[categoria].astype("string").str.strip().str.upper().isin(
            {"#N/D", "N/D"}
        )
        df.loc[marcador_ausente, categoria] = pd.NA
        df[categoria] = df[categoria].fillna("Sem Categoria")

    # Preserve os registros de gênero ausente com um rótulo explícito.
    genero = localizar_coluna(df.columns, COLUNAS_GENERO)
    if genero:
        df[genero] = df[genero].fillna("Não informado")

    # Removemos registros idênticos completos, não todas as linhas com o mesmo CO_ID:
    # uma compra pode conter vários produtos e, portanto, repetir seu identificador.
    duplicatas = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()
    relatorio["duplicatas_removidas"] = duplicatas

    # Localize as colunas da base para converter tipos e validar a regra da compra.
    compra = localizar_coluna(df.columns, COLUNAS_COMPRA)
    cliente = localizar_coluna(df.columns, COLUNAS_CLIENTE)
    filhos = localizar_coluna(df.columns, COLUNAS_FILHOS)
    data = localizar_coluna(df.columns, COLUNAS_DATA)
    relatorio["coluna_compra"] = compra
    relatorio["coluna_cliente"] = cliente
    relatorio["coluna_filhos"] = filhos

    # Identificadores são numéricos; valores que não puderem ser convertidos viram nulos.
    if compra:
        df[compra] = pd.to_numeric(df[compra], errors="coerce").astype("Int64")
        relatorio["compras_unicas"] = int(df[compra].nunique(dropna=True))
        relatorio["linhas_com_compra_ausente"] = int(df[compra].isna().sum())

    if cliente:
        df[cliente] = pd.to_numeric(df[cliente], errors="coerce").astype("Int64")

    # Filhos é uma contagem inteira; a mediana arredondada preenche eventuais ausências
    # sem remover clientes. Se todos os valores forem ausentes, mantenha-os ausentes.
    if filhos:
        df[filhos] = pd.to_numeric(df[filhos], errors="coerce")
        ausentes_filhos = int(df[filhos].isna().sum())
        if ausentes_filhos and df[filhos].notna().any():
            mediana = int(round(float(df[filhos].median())))
            df[filhos] = df[filhos].fillna(mediana)
            relatorio["filhos_imputados"] = ausentes_filhos
            relatorio["imputacao_filhos"] = mediana
        df[filhos] = df[filhos].astype("Int64")

    # Interprete datas no formato dia/mês/ano e descarte datas inválidas ou sem compra,
    # pois elas não permitem análises temporais nem agrupamentos confiáveis por pedido.
    if data:
        df[data] = pd.to_datetime(
            df[data], format="%d/%m/%Y", errors="coerce"
        )
        datas_invalidas = int(df[data].isna().sum())
        relatorio["datas_invalidas"] = datas_invalidas

    # Valide antes de excluir linhas com data ausente para não esconder uma compra
    # que mistura datas válidas e inválidas.
    if compra and cliente and data:
        compras = df.dropna(subset=[compra]).groupby(compra).agg(
            clientes=(cliente, lambda valores: valores.nunique(dropna=True)),
            cliente_ausente=(cliente, lambda valores: valores.isna().any()),
            datas=(data, lambda valores: valores.nunique(dropna=True)),
            data_ausente=(data, lambda valores: valores.isna().any()),
        )
        inconsistente = (
            compras["clientes"].ne(1)
            | compras["cliente_ausente"]
            | compras["datas"].ne(1)
            | compras["data_ausente"]
        )
        relatorio["compras_com_varios_clientes_ou_datas"] = int(inconsistente.sum())
        relatorio["regra_compra_validada"] = True
    else:
        relatorio["regra_compra_validada"] = False

    # Datas e identificadores de compra são campos essenciais para as análises
    # temporais e por pedido; remova as linhas sem esses valores após validá-las.
    essenciais = [coluna for coluna in (data, compra) if coluna]
    antes = len(df)
    if essenciais:
        df = df.dropna(subset=essenciais).copy()
    relatorio["registros_sem_data_ou_compra_removidos"] = antes - len(df)

    # Trate dimensões físicas somente se existirem na versão recebida da base.
    dimensoes = [
        coluna
        for coluna in df.columns
        if normalizar_nome(coluna) in {normalizar_nome(nome) for nome in COLUNAS_DIMENSOES}
    ]
    relatorio["dimensoes_encontradas"] = dimensoes
    for coluna in dimensoes:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
        if df[coluna].isna().any() and df[coluna].notna().any():
            mediana = float(df[coluna].median())
            quantidade = int(df[coluna].isna().sum())
            df[coluna] = df[coluna].fillna(mediana)
            relatorio.setdefault("dimensoes_imputadas", {})[coluna] = {
                "quantidade": quantidade,
                "mediana": mediana,
            }

    relatorio["registros_finais"] = len(df)
    return df, relatorio


def estatisticas_filhos(df: pd.DataFrame, coluna_filhos: str | None, coluna_cliente: str | None) -> pd.Series | None:
    if not coluna_filhos:
        return None

    # Cada cliente pode aparecer em várias linhas de produto, mas seu perfil deve
    # contribuir uma única vez para a estatística descritiva.
    valores = df[[coluna_filhos] + ([coluna_cliente] if coluna_cliente else [])].copy()
    valores = valores.dropna(subset=[coluna_filhos])
    if coluna_cliente:
        # A mesma pessoa aparece em várias linhas de produto; conte seu perfil uma vez.
        valores = valores.drop_duplicates(subset=[coluna_cliente])
    return valores[coluna_filhos].describe(percentiles=[0.25, 0.5, 0.75])


def agrupar(
    df: pd.DataFrame, categoria: str | None, genero: str | None, compra: str | None
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    if not compra:
        return None, None

    # Mostre tanto o volume de linhas quanto os pedidos distintos em cada grupo.
    def resumir(coluna: str | None) -> pd.DataFrame | None:
        if not coluna:
            return None
        return (
            df.groupby(coluna, dropna=False)
            .agg(
                registros=(compra, "size"),
                compras_unicas=(compra, "nunique"),
            )
            .sort_values("compras_unicas", ascending=False)
        )

    return resumir(genero), resumir(categoria)


def conclusoes(
    df: pd.DataFrame,
    relatorio: dict[str, object],
    estatisticas: pd.Series | None,
    por_genero: pd.DataFrame | None,
    por_categoria: pd.DataFrame | None,
) -> list[str]:
    # Gere conclusões a partir dos resultados, limitadas à faixa pedida no enunciado.
    itens = [
        (
            f"A base ficou com {len(df):,} registros após a limpeza; "
            f"{relatorio['duplicatas_removidas']:,} linhas idênticas foram removidas."
        ).replace(",", ".")
    ]

    if por_genero is not None and not por_genero.empty:
        itens.append(
            f"Maior número de compras únicas por gênero: "
            f"{por_genero.index[0]} ({int(por_genero.iloc[0]['compras_unicas']):,}).".replace(",", ".")
        )
    if por_categoria is not None and not por_categoria.empty:
        itens.append(
            f"Categoria com mais compras únicas: {por_categoria.index[0]} "
            f"({int(por_categoria.iloc[0]['compras_unicas']):,}).".replace(",", ".")
        )
    if estatisticas is not None:
        itens.append(
            f"Número de filhos por cliente: média {estatisticas['mean']:.2f}, "
            f"mediana {estatisticas['50%']:.0f}; estatística calculada uma vez por cliente."
        )
    if relatorio.get("compras_com_varios_clientes_ou_datas", 0):
        itens.append(
            "Há identificadores de compra associados a clientes ou datas inconsistentes; "
            "verifique a regra de negócio antes de usar esses registros."
        )
    if not relatorio["dimensoes_encontradas"]:
        itens.append(
            "A base não contém colunas de dimensões físicas; não havia valores desse tipo para imputar."
        )
    if not localizar_coluna(df.columns, ("VALOR", "PRECO", "PREÇO", "FATURAMENTO", "AMOUNT", "SALES")):
        itens.append(
            "Não há coluna de preço ou faturamento: os agrupamentos comparam quantidade de registros "
            "e compras únicas, não valor monetário vendido."
        )
    return itens[:6]


def executar(caminho_entrada: Path, caminho_saida: Path) -> None:
    # Execute as etapas na ordem da análise: diagnóstico, limpeza, resumos e exportação.
    original = carregar_base(caminho_entrada)
    relatar_qualidade(original)
    limpa, relatorio = limpar_base(original)
    categoria = localizar_coluna(limpa.columns, COLUNAS_CATEGORIA)
    genero = localizar_coluna(limpa.columns, COLUNAS_GENERO)
    compra = localizar_coluna(limpa.columns, COLUNAS_COMPRA)
    cliente = localizar_coluna(limpa.columns, COLUNAS_CLIENTE)
    filhos = localizar_coluna(limpa.columns, COLUNAS_FILHOS)

    estatisticas = estatisticas_filhos(limpa, filhos, cliente)
    por_genero, por_categoria = agrupar(limpa, categoria, genero, compra)

    print("\nResumo da limpeza:")
    print(f"Colunas vazias removidas: {relatorio['colunas_vazias_removidas']}")
    print(f"Duplicatas removidas: {relatorio['duplicatas_removidas']:,}".replace(",", "."))
    print(f"Datas inválidas/nulas: {relatorio.get('datas_invalidas', 'coluna não encontrada')}")
    print(f"Registros removidos por data/compra ausente: {relatorio['registros_sem_data_ou_compra_removidos']}")
    print("\nTipos de dados após limpeza:")
    print(limpa.dtypes.to_string())
    if relatorio.get("compras_unicas") is not None:
        print(f"Compras únicas: {relatorio['compras_unicas']:,}".replace(",", "."))
        if relatorio["regra_compra_validada"]:
            inconsistencias = relatorio["compras_com_varios_clientes_ou_datas"]
            status = "aprovada" if inconsistencias == 0 else "reprovada"
            print(
                f"Regra de CO_ID {status}: {inconsistencias} compra(s) associada(s) "
                "a mais de um cliente/data ou com cliente/data ausente."
            )
            print(
                "CO_ID pode se repetir em linhas distintas porque uma compra pode "
                "conter vários produtos."
            )
        else:
            print(
                "Regra de CO_ID não validada: não foi possível localizar as colunas "
                "de cliente e data necessárias."
            )
    if relatorio.get("dimensoes_encontradas"):
        print(f"Dimensões físicas encontradas: {relatorio['dimensoes_encontradas']}")
    else:
        print("Dimensões físicas: não existem colunas correspondentes na base.")

    if estatisticas is not None:
        print("\nEstatísticas de número de filhos por cliente:")
        print(estatisticas.to_string())
        moda = limpa[filhos].mode()
        print(f"Moda: {', '.join(str(int(valor)) for valor in moda)}")
    else:
        print("\nColuna de número de filhos não encontrada; estatísticas não calculadas.")

    # Exiba os dois agrupamentos exigidos quando as colunas correspondentes existirem.
    for titulo, tabela in (("Agrupamento por gênero", por_genero), ("Agrupamento por categoria", por_categoria)):
        if tabela is not None:
            print(f"\n{titulo} (registros e compras únicas):")
            print(tabela.to_string())
        else:
            print(f"\n{titulo}: coluna necessária não encontrada.")

    # Salve a base tratada para compor a entrega do projeto.
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    limpa.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
    print(f"\nBase limpa salva em: {caminho_saida}")

    print("\nConclusões:")
    for conclusao in conclusoes(
        limpa, relatorio, estatisticas, por_genero, por_categoria
    ):
        print(f"- {conclusao}")


def main() -> None:
    # Permita personalizar os caminhos mantendo nomes padrão para execução simples.
    parser = argparse.ArgumentParser(description="Executa a análise exploratória da base Varejo.")
    parser.add_argument("--entrada", type=Path, default=Path("Base Varejo.csv"), help="Caminho do CSV original.")
    parser.add_argument("--saida", type=Path, default=Path("df_limpo.csv"), help="Caminho do CSV limpo.")
    args = parser.parse_args()
    executar(args.entrada, args.saida)


if __name__ == "__main__":
    main()
