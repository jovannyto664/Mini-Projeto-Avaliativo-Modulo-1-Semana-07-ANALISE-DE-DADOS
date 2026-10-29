import tempfile
import unittest
from pathlib import Path

import pandas as pd

from analise_varejo import carregar_base, limpar_base, estatisticas_filhos, agrupar


class AnaliseVarejoTests(unittest.TestCase):
    def test_limpeza_preserva_compra_com_varios_produtos_e_remove_duplicata_exata(self):
        origem = pd.DataFrame(
            {
                "DATA": ["01/02/2019", "01/02/2019", "01/02/2019", "31/02/2019"],
                "CO_ID": ["100", "100", "100", "101"],
                "CL_ID": ["10", "10", "10", "11"],
                "CL_GENERO": ["F", "F", "F", "M"],
                "CL_FHL": ["2", "2", "2", "1"],
                "PR_CAT": ["ALIMENTOS", "ALIMENTOS", None, "ALIMENTOS"],
                "PR_ID": ["1", "3", "4", "2"],
            }
        )
        origem = pd.concat([origem, origem.iloc[[0]]], ignore_index=True)

        limpa, relatorio = limpar_base(origem)

        self.assertEqual(relatorio["duplicatas_removidas"], 1)
        self.assertEqual(len(limpa), 3)
        self.assertEqual(limpa["CO_ID"].nunique(), 1)
        self.assertEqual(limpa["PR_CAT"].iloc[2], "Sem Categoria")
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(limpa["DATA"]))

    def test_categoria_nao_disponivel_recebe_rotulo_padrao(self):
        origem = pd.DataFrame(
            {
                "CO_ID": ["100"],
                "CL_GENERO": ["F"],
                "PR_CAT": ["#N/D"],
            }
        )

        limpa, _ = limpar_base(origem)

        self.assertEqual(limpa.loc[0, "PR_CAT"], "Sem Categoria")

    def test_stats_contam_cada_cliente_uma_vez_e_agrupam_compras(self):
        df = pd.DataFrame(
            {
                "CL_ID": [1, 1, 2],
                "CL_FHL": [2, 2, 0],
                "CO_ID": [10, 10, 11],
                "CL_GENERO": ["F", "F", "M"],
                "PR_CAT": ["A", "B", "A"],
            }
        )

        stats = estatisticas_filhos(df, "CL_FHL", "CL_ID")
        por_genero, por_categoria = agrupar(df, "PR_CAT", "CL_GENERO", "CO_ID")

        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["mean"], 1)
        self.assertEqual(por_genero.loc["F", "compras_unicas"], 1)
        self.assertEqual(por_categoria.loc["A", "compras_unicas"], 2)

    def test_validacao_detecta_compra_associada_a_clientes_diferentes(self):
        origem = pd.DataFrame(
            {
                "DATA": ["01/02/2019", "01/02/2019", "02/02/2019"],
                "CO_ID": ["100", "100", "101"],
                "CL_ID": ["10", "11", "12"],
                "CL_GENERO": ["F", "M", "F"],
                "CL_FHL": ["2", "1", "0"],
                "PR_CAT": ["A", "B", "A"],
            }
        )

        _, relatorio = limpar_base(origem)

        self.assertTrue(relatorio["regra_compra_validada"])
        self.assertEqual(relatorio["compras_com_varios_clientes_ou_datas"], 1)

    def test_validacao_nao_esconde_data_invalida_antes_da_limpeza(self):
        origem = pd.DataFrame(
            {
                "DATA": ["01/02/2019", "31/02/2019"],
                "CO_ID": ["100", "100"],
                "CL_ID": ["10", "10"],
                "CL_GENERO": ["F", "F"],
                "CL_FHL": ["2", "2"],
                "PR_CAT": ["A", "B"],
            }
        )

        limpa, relatorio = limpar_base(origem)

        self.assertEqual(relatorio["compras_com_varios_clientes_ou_datas"], 1)
        self.assertEqual(relatorio["datas_invalidas"], 1)
        self.assertEqual(len(limpa), 1)

    def test_carrega_csv_com_separador_ponto_e_virgula(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "Base Varejo.csv"
            caminho.write_text("DATA;CO_ID\n01/02/2019;10\n", encoding="latin1")

            df = carregar_base(caminho)

        self.assertEqual(list(df.columns), ["DATA", "CO_ID"])
        self.assertEqual(df.loc[0, "CO_ID"], 10)


if __name__ == "__main__":
    unittest.main()
