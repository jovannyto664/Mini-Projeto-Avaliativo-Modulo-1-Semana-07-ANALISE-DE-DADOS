# Análise exploratória de dados de varejo

Mini-projeto avaliativo do Módulo 1 — Semana 07. O script `analise_varejo.py` usa pandas para carregar, avaliar, limpar e resumir a base Varejo.

## Como obter os dados e executar

1. Baixe `Base Varejo.csv` na página [Base Varejo no Kaggle](https://www.kaggle.com/datasets/namespaiva/base-varejo).
2. Salve o arquivo como `Varejo.csv` na pasta do projeto.
3. Instale a dependência com `python -m pip install -r requirements.txt`.
4. Execute `python analise_varejo.py`. Para outros caminhos, use `python analise_varejo.py --entrada caminho\Varejo.csv --saida caminho\df_limpo.csv`.

O programa imprime os diagnósticos, estatísticas, agrupamentos e conclusões no terminal e cria `df_limpo.csv`. O arquivo gerado não está versionado; rode o script para produzi-lo localmente.

Para executar os testes automatizados: `python -m unittest discover -s tests -v`.

## Etapas de ETL e decisões de qualidade

- **Extração:** leitura do CSV com separador `;` e codificação `latin1`, características do arquivo publicado no Kaggle.
- **Transformação:** colunas sem nome e totalmente vazias são descartadas; categorias vazias recebem `"Sem Categoria"`; os campos de data, compra, cliente e número de filhos são convertidos para tipos apropriados.
- **Nulos:** se houver número de filhos ausente, o script usa a mediana arredondada, preservando as linhas; dimensões físicas presentes são imputadas pela mediana da própria coluna. A base consultada não possui dimensões físicas. Datas e identificadores de compra ausentes são removidos por serem necessários para a análise temporal e de compras.
- **Duplicatas:** são removidas apenas linhas inteiramente idênticas. `CO_ID` repetido não é tratado como duplicata: o mesmo pedido pode possuir vários produtos.
- **Agrupamentos:** comparam registros e compras únicas por gênero e categoria; não estimam valores de vendas.

Qualidade de dados é a adequação, consistência, completude e validade dos dados para um uso específico. ETL significa extrair dados de uma fonte, transformá-los para corrigir ou padronizar sua estrutura e carregá-los para análise ou uso posterior.

## Insights da base analisada

Na versão da base analisada para este projeto, foram observados os seguintes resultados:

- A leitura encontrou 830.000 registros e 14 colunas; quatro colunas finais estavam sem nome e completamente vazias.
- Foram identificadas 96.553 linhas exatamente repetidas; após removê-las, restaram 733.447 registros.
- Há 18.471 identificadores de compra (`CO_ID`). O identificador se repete entre linhas de produtos e não deve ser tratado como uma chave única por linha.
- O gênero `F` aparece em 9.615 compras únicas e `M` em 8.856.
- `ALIMENTOS` é a categoria com mais compras únicas (18.267); categorias podem compartilhar uma compra e, por isso, essas contagens não devem ser somadas como se fossem mutuamente exclusivas.
- Considerando um registro por cliente (1.000 clientes), o número de filhos tem média 1,136, mediana 0, desvio padrão aproximado 1,413, moda 0, mínimo 0, máximo 4 e quartis 0, 0 e 2. A categoria `#N/D` é tratada como `"Sem Categoria"`; a base não possui dimensões físicas nem preço/faturamento.

O programa imprime os resultados atualizados sempre que for executado. Os agrupamentos descrevem contagem de linhas e compras distintas, não valor monetário vendido.

## Estrutura

- `analise_varejo.py`: análise e geração da base limpa.
- `requirements.txt`: dependência necessária.
- `README_NomeDoAluno_Analise_de_Dados_T1.md`: instruções de execução para entrega; substitua `NomeDoAluno` pelo seu nome completo.
