import unittest

from checar_cv import achar, ler_termos, quebras_hifen


class TestChecarCV(unittest.TestCase):
    def test_ler_termos_marca_obrigatorio_e_gap(self):
        termos = ler_termos("# comentário\n*Python\n*!Kafka\nDocker\n\n")
        self.assertEqual(termos, [("Python", True, False), ("Kafka", True, True), ("Docker", False, False)])

    def test_achar_respeita_fronteira_de_palavra(self):
        texto = "Experiência com JavaScript e Node.js"
        self.assertFalse(achar("Java", texto))
        self.assertTrue(achar("javascript", texto))
        self.assertTrue(achar("Node.js", texto))

    def test_achar_ignora_quebra_de_linha_dentro_do_termo(self):
        self.assertTrue(achar("Power Automate", "fluxos em Power\nAutomate e n8n"))

    def test_achar_termo_com_simbolo(self):
        self.assertTrue(achar("C#", "C#, Python"))
        self.assertFalse(achar("30%", "ganho de 130%"))

    def test_achar_alternativas_com_barra_vertical(self):
        self.assertTrue(achar("PyTorch|TensorFlow", "modelos em TensorFlow"))
        self.assertFalse(achar("PyTorch|TensorFlow", "modelos em Keras"))

    def test_quebras_hifen_pega_palavra_cortada_no_fim_da_linha(self):
        texto = "agentes com Lang-\nChain e end-to-end\nok"
        self.assertEqual(quebras_hifen(texto), ["Lang-"])


if __name__ == "__main__":
    unittest.main()
