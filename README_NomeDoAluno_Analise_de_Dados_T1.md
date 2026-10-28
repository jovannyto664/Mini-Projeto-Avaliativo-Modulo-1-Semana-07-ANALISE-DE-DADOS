# Instruções de execução — Análise de Dados T1

1. Instale Python 3.10 ou superior.
2. Baixe a base `Base Varejo.csv` pela página [Base Varejo no Kaggle](https://www.kaggle.com/datasets/namespaiva/base-varejo) e salve-a na pasta do projeto com o nome `Varejo.csv`.
3. No terminal do VS Code, execute `python -m pip install -r requirements.txt`.
4. Execute `python analise_varejo.py`.
5. Consulte os diagnósticos, estatísticas, agrupamentos e conclusões impressos no terminal. O programa também cria o arquivo `df_limpo.csv`.

Se o arquivo CSV estiver em outra pasta, informe seu caminho: `python analise_varejo.py --entrada caminho\Varejo.csv --saida caminho\df_limpo.csv`.

Antes de entregar, renomeie este arquivo para `README_SeuNome_Analise_de_Dados_T1.md`, usando seu nome completo.
