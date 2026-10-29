"""Aqui eu faço a análise exploratória da base Varejo para o mini-projeto."""

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
    """Aqui eu padronizo nomes para encontrar colunas mesmo com acentos e espaços."""
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
    """Aqui eu leio o CSV do Kaggle com o separador e a codificação dessa base."""
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}. Baixe o CSV indicado no README."
        )

    # Aqui eu leio o CSV com ponto e vírgula e a codificação Latin-1 usada pela base.
    df = pd.read_csv(caminho, sep=";", encoding="latin1", low_memory=False)
    df.columns = [str(coluna).strip() for coluna in df.columns]
    # Eu também considero vazias as células que só têm espaços.
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    return df


def relatar_qualidade(df: pd.DataFrame) -> int:
    # Primeiro eu mostro o tamanho, os tipos e os valores ausentes da base original.
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

    # Eu removo as colunas excedentes apenas quando elas estão completamente vazias.
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

    # Como a base marca algumas categorias como #N/D, eu trato isso como valor ausente
    # e preencho com "Sem Categoria", assim como faço com as células vazias.
    categoria = localizar_coluna(df.columns, COLUNAS_CATEGORIA)
    if categoria:
        marcador_ausente = df[categoria].astype("string").str.strip().str.upper().isin(
            {"#N/D", "N/D"}
        )
        df.loc[marcador_ausente, categoria] = pd.NA
        df[categoria] = df[categoria].fillna("Sem Categoria")

    # Quando falta o gênero, eu mantenho o registro e uso um rótulo explícito.
    genero = localizar_coluna(df.columns, COLUNAS_GENERO)
    if genero:
        df[genero] = df[genero].fillna("Não informado")

    # Eu removo só as linhas totalmente iguais. Não removo CO_ID repetido, porque
    # uma compra pode ter vários produtos e aparecer em várias linhas.
    duplicatas = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()
    relatorio["duplicatas_removidas"] = duplicatas

    # Aqui eu encontro as colunas que preciso converter e usar na regra de compra.
    compra = localizar_coluna(df.columns, COLUNAS_COMPRA)
    cliente = localizar_coluna(df.columns, COLUNAS_CLIENTE)
    filhos = localizar_coluna(df.columns, COLUNAS_FILHOS)
    data = localizar_coluna(df.columns, COLUNAS_DATA)
    relatorio["coluna_compra"] = compra
    relatorio["coluna_cliente"] = cliente
    relatorio["coluna_filhos"] = filhos

    # Eu converto os identificadores em números; valores inválidos passam a nulos.
    if compra:
        df[compra] = pd.to_numeric(df[compra], errors="coerce").astype("Int64")
        relatorio["compras_unicas"] = int(df[compra].nunique(dropna=True))
        relatorio["linhas_com_compra_ausente"] = int(df[compra].isna().sum())

    if cliente:
        df[cliente] = pd.to_numeric(df[cliente], errors="coerce").astype("Int64")

    # Eu trato número de filhos como contagem inteira e preencho os nulos com a
    # mediana arredondada para não excluir clientes; se tudo estiver nulo, eu mantenho assim.
    if filhos:
        df[filhos] = pd.to_numeric(df[filhos], errors="coerce")
        ausentes_filhos = int(df[filhos].isna().sum())
        if ausentes_filhos and df[filhos].notna().any():
            mediana = int(round(float(df[filhos].median())))
            df[filhos] = df[filhos].fillna(mediana)
            relatorio["filhos_imputados"] = ausentes_filhos
            relatorio["imputacao_filhos"] = mediana
        df[filhos] = df[filhos].astype("Int64")

    # Eu converto as datas do formato dia/mês/ano e transformo datas inválidas em
    # nulas para identificá-las e removê-las depois, antes das análises.
    if data:
        df[data] = pd.to_datetime(
            df[data], format="%d/%m/%Y", errors="coerce"
        )
        datas_invalidas = int(df[data].isna().sum())
        relatorio["datas_invalidas"] = datas_invalidas

    # Antes de remover datas inválidas, eu verifico se cada compra pertence a um
    # único cliente e a uma única data, sem esconder compras inconsistentes.
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

    # Depois da validação, eu removo linhas sem data ou sem compra, pois não consigo
    # usá-las nas análises por data e por pedido.
    essenciais = [coluna for coluna in (data, compra) if coluna]
    antes = len(df)
    if essenciais:
        df = df.dropna(subset=essenciais).copy()
    relatorio["registros_sem_data_ou_compra_removidos"] = antes - len(df)

    # Se a base tiver dimensões físicas, eu converto os valores e preencho os nulos
    # com a mediana de cada coluna; se não tiver, não invento esses dados.
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

    # Como um cliente pode aparecer em várias linhas de produto, eu conto o número
    # de filhos dele só uma vez nas estatísticas.
    valores = df[[coluna_filhos] + ([coluna_cliente] if coluna_cliente else [])].copy()
    valores = valores.dropna(subset=[coluna_filhos])
    if coluna_cliente:
        # Aqui eu retiro as repetições de cliente antes de calcular as estatísticas.
        valores = valores.drop_duplicates(subset=[coluna_cliente])
    return valores[coluna_filhos].describe(percentiles=[0.25, 0.5, 0.75])


def agrupar(
    df: pd.DataFrame, categoria: str | None, genero: str | None, compra: str | None
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    if not compra:
        return None, None

    # Para cada grupo, eu mostro o número de linhas e quantas compras diferentes há.
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
    # Aqui eu monto de três a seis conclusões a partir dos resultados da análise.
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
    # Aqui eu organizo o fluxo: verifico os dados, limpo a base, analiso e salvo o CSV.
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

    # Eu mostro os agrupamentos por gênero e categoria quando encontro essas colunas.
    for titulo, tabela in (("Agrupamento por gênero", por_genero), ("Agrupamento por categoria", por_categoria)):
        if tabela is not None:
            print(f"\n{titulo} (registros e compras únicas):")
            print(tabela.to_string())
        else:
            print(f"\n{titulo}: coluna necessária não encontrada.")

    # Por fim, eu salvo a base limpa para incluir no projeto.
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    limpa.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
    print(f"\nBase limpa salva em: {caminho_saida}")

    print("\nConclusões:")
    for conclusao in conclusoes(
        limpa, relatorio, estatisticas, por_genero, por_categoria
    ):
        print(f"- {conclusao}")


def main() -> None:
    # Eu aceito caminhos personalizados e uso nomes padrão para facilitar a execução.
    parser = argparse.ArgumentParser(description="Executa a análise exploratória da base Varejo.")
    parser.add_argument("--entrada", type=Path, default=Path("Base Varejo.csv"), help="Caminho do CSV original.")
    parser.add_argument("--saida", type=Path, default=Path("df_limpo.csv"), help="Caminho do CSV limpo.")
    args = parser.parse_args()
    executar(args.entrada, args.saida)


if __name__ == "__main__":
    main()
