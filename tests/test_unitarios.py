"""Testes unitários dos helpers puros (sem PDF, sem fixtures).

Protegem as funções de normalização, casamento de nomes e interpretação de
valores antes da refatoração. Testes expectedFailure documentam DEFEITOS
CONHECIDOS que não devem ser mascarados.
"""
import unittest

from tests import util  # garante sys.path do projeto  # noqa: F401


class TestNormalizacao(unittest.TestCase):

    def test_chave_remove_acentos_e_caixa(self):
        from identificador import chave
        self.assertEqual(chave('Técnico Judiciário'), 'tecnico judiciario')
        self.assertEqual(chave('ÁREA ADMINISTRATIVA'), 'area administrativa')

    def test_canon_remove_codigo_e_tokens_de_orgao(self):
        from conteudo import canon
        self.assertEqual(
            canon('01 – Analista Judiciário – Área Judiciária'),
            canon('Analista Judiciário – Área Judiciária'))
        self.assertEqual(canon('Analista TRF4 Judiciário'),
                         canon('Analista Judiciário'))

    def test_variantes_de_normalizacao_sao_equivalentes_em_ascii(self):
        """As 4+ funções de normalização devem concordar em entradas simples;
        este teste congela a equivalência antes da unificação futura."""
        from identificador import normalizar as norm_ident
        from dados_compartilhados import normalizar as norm_dc
        from vagas_tabelas import normalizar as norm_vt
        from cargo_dados import norm as norm_cd
        entrada = 'Analista Judiciário – Área Administrativa'
        esperado = 'analista judiciario area administrativa'
        self.assertEqual(norm_ident(entrada), esperado)
        self.assertEqual(norm_cd(entrada), esperado)
        # As variantes abaixo preservam pontuação/traços por desenho atual.
        self.assertEqual(norm_dc('Técnico  Judiciário').split(),
                         ['tecnico', 'judiciario'])
        self.assertEqual(norm_vt(' Cadastro  de Reserva '),
                         'cadastro de reserva')


class TestCasamentoDeNomes(unittest.TestCase):

    def test_matches_por_codigo(self):
        from conteudo import matches
        self.assertTrue(matches('01 – Analista Judiciário – Área Judiciária',
                                '01 – Analista Judiciário'))
        self.assertFalse(matches('01 – Analista Judiciário',
                                 '02 – Analista Judiciário'))

    def test_matches_por_nome_canonico(self):
        from conteudo import matches
        self.assertTrue(matches(
            'Analista Judiciário – Área Apoio Especializado – Especialidade '
            'Contabilidade',
            'Analista Judiciário – Área Apoio Especializado – Contabilidade'))
        self.assertFalse(matches('Analista Judiciário – Área Judiciária',
                                 'Técnico Judiciário – Área Administrativa'))

    def test_nomes_equivalentes_tolera_uma_palavra_proxima(self):
        from identificador import nomes_equivalentes
        self.assertTrue(nomes_equivalentes(
            'Analista Judiciário Área Administrativa',
            'Analista Judiciario Área Administrativa'))
        self.assertFalse(nomes_equivalentes(
            'Analista Judiciário Área Administrativa',
            'Técnico Judiciário Área Administrativa'))

    def test_nome_valido_rejeita_residuos(self):
        from identificador import nome_valido
        self.assertTrue(nome_valido('Investigador de Polícia I'))
        self.assertFalse(nome_valido('Policial'))
        self.assertFalse(nome_valido('o referido concurso público'))


class TestInterpretarVagas(unittest.TestCase):

    def test_numeros_e_cadastro_de_reserva(self):
        from vagas_tabelas import interpretar_vagas
        self.assertEqual(interpretar_vagas('165'), '165')
        self.assertEqual(interpretar_vagas('1.024'), '1.024')
        self.assertEqual(interpretar_vagas('CR'), 'CR')
        self.assertEqual(interpretar_vagas('c.r.'), 'CR')
        self.assertEqual(interpretar_vagas('Cadastro de Reserva'), 'CR')

    @unittest.expectedFailure
    def test_sobrescrito_de_nota_de_rodape_nao_vira_digito(self):
        """FALHA CONHECIDA (V3.0.11): em vagas_tabelas.interpretar_vagas a
        normalização NFKD converte sobrescritos (¹²³…) em dígitos comuns
        ANTES da regex que deveria removê-los. Resultado: '10¹' (10 vagas
        com nota de rodapé) é interpretado como '101' vagas — corrupção
        silenciosa do total de vagas em tabelas com notas.

        Quando o defeito for corrigido, este teste dará "unexpected
        success" e deverá virar obrigatório.
        """
        from vagas_tabelas import interpretar_vagas
        self.assertEqual(interpretar_vagas('10¹'), '10')

    def test_valores_nao_numericos_sao_rejeitados(self):
        from vagas_tabelas import interpretar_vagas
        self.assertIsNone(interpretar_vagas('Ensino Superior'))
        self.assertIsNone(interpretar_vagas('R$ 110,00'))
        self.assertIsNone(interpretar_vagas(''))


class TestParserConteudo(unittest.TestCase):

    def test_heading_reconhece_cabecalhos_de_conteudo(self):
        from conteudo import heading
        self.assertTrue(heading('CONTEÚDO PROGRAMÁTICO'))
        self.assertTrue(heading('ANEXO I – CONTEÚDOS PROGRAMÁTICOS'))
        self.assertFalse(heading('CRONOGRAMA'))

    def test_clean_remove_rodapes(self):
        from conteudo import clean
        self.assertFalse(clean('www.pciconcursos.com.br'))
        self.assertFalse(clean('42'))
        self.assertTrue(clean('Direito Constitucional: conceito.'))

    def test_codigo_grupos_extrai_prefixo_numerico(self):
        from conteudo import _codigo_grupos
        self.assertEqual(_codigo_grupos('01 – Analista Judiciário'), '01')
        self.assertEqual(_codigo_grupos('123. Técnico'), '123')
        self.assertIsNone(_codigo_grupos('Analista Judiciário'))

    def test_assuntos_numerados_divide_topicos_ascii(self):
        from conteudo import _assuntos_numerados
        partes = [(1, '1.1 Conceito de direito. 1.2 Fontes do direito. '
                      '1.3 Normas.')]
        assuntos = _assuntos_numerados(partes)
        self.assertEqual(len(assuntos), 3)
        self.assertTrue(assuntos[0].startswith('1.1'))
        self.assertTrue(assuntos[2].startswith('1.3'))

    def test_assuntos_numerados_ignora_versao_de_software(self):
        from conteudo import _assuntos_numerados
        partes = [(1, '1.1 Editor de textos LibreOffice 7.4 e recursos. '
                      '1.2 Planilhas.')]
        assuntos = _assuntos_numerados(partes)
        self.assertEqual(len(assuntos), 2)

    @unittest.expectedFailure
    def test_assuntos_numerados_topico_iniciado_por_acento(self):
        """FALHA CONHECIDA (V3.0.11): a classe de caracteres do lookahead em
        _assuntos_numerados foi corrompida por encoding (conteudo.py:185,
        '[A-Za-z?-?(?"\']'). Tópicos iniciados por letra acentuada
        (Ética, Órgãos, Índice, Água…) não são reconhecidos como marcadores
        e são fundidos ao tópico anterior.

        Quando o defeito for corrigido, este teste dará "unexpected success"
        e deverá virar um teste obrigatório.
        """
        from conteudo import _assuntos_numerados
        partes = [(1, '1.1 Conceito de moral. 1.2 Ética no serviço público. '
                      '1.3 Deveres do servidor.')]
        assuntos = _assuntos_numerados(partes)
        self.assertEqual(
            len(assuntos), 3,
            f'tópico acentuado foi fundido: {assuntos}')


class TestDeduplicacaoCargos(unittest.TestCase):

    def test_dedup_por_chave_e_idempotente(self):
        from identificador import chave
        nomes = ['Analista Judiciário', 'ANALISTA JUDICIARIO',
                 'Técnico Judiciário']

        def dedup(itens):
            vistos, saida = set(), []
            for n in itens:
                k = chave(n)
                if k in vistos:
                    continue
                vistos.add(k)
                saida.append(n)
            return saida

        uma_vez = dedup(nomes)
        self.assertEqual(uma_vez, ['Analista Judiciário',
                                   'Técnico Judiciário'])
        self.assertEqual(dedup(uma_vez), uma_vez)


if __name__ == '__main__':
    unittest.main()
