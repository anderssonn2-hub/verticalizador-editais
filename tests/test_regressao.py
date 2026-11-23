"""Testes de regressão golden: congelam o comportamento atual (V3.0.11 DEV).

Comparam o pipeline espelhado (tests.pipeline_atual) executado sobre as
fixtures de texto com os snapshots em tests/golden/<edital>.json.

Se um destes testes falhar após uma mudança de código, o comportamento
observável do extrator mudou: a mudança deve ser revisada e, se for
intencional e correta, o golden deve ser regenerado de forma consciente
(.venv\\Scripts\\python.exe -m tests.gerar_fixtures).
"""
import unittest

from tests.util import (
    EDITAIS, tem_fixtures, carregar_paginas, carregar_golden, caminho_pdf,
)
from tests.pipeline_atual import executar

SECOES_SEM_PDF = [
    'n_paginas', 'intervalo_conteudo', 'cargos', 'identificacao',
    'cronograma', 'prova', 'blocos', 'conteudo', 'cobertura_linhas',
]
SECOES_COM_PDF = ['dados', 'vagas_tabelas']

_cache = {}


def _snapshot(nome):
    if nome not in _cache:
        pgs = carregar_paginas(nome)
        pdf = caminho_pdf(nome)
        pdf_bytes = pdf.read_bytes() if pdf.is_file() else None
        _cache[nome] = (executar(pgs, pdf_bytes), pdf_bytes is not None)
    return _cache[nome]


class TestRegressaoGolden(unittest.TestCase):
    maxDiff = 5000

    def _comparar(self, nome, secao):
        if not tem_fixtures(nome):
            self.skipTest(
                f'Fixtures ausentes para {nome}: coloque o PDF em '
                f'tests/fixtures/pdfs/{nome}.pdf e rode '
                f'python -m tests.gerar_fixtures')
        atual, com_pdf = _snapshot(nome)
        if secao in SECOES_COM_PDF and not com_pdf:
            self.skipTest(
                f'PDF ausente (tests/fixtures/pdfs/{nome}.pdf); '
                f'seção "{secao}" depende da leitura de tabelas do PDF.')
        golden = carregar_golden(nome)
        if secao == 'conteudo':
            # Comparação por cargo para localizar divergências.
            self.assertEqual(sorted(golden[secao]), sorted(atual[secao]),
                             'Conjunto de cargos com conteúdo divergiu.')
            for cargo in golden[secao]:
                with self.subTest(cargo=cargo):
                    self.assertEqual(golden[secao][cargo],
                                     atual[secao][cargo])
        else:
            self.assertEqual(golden[secao], atual[secao])


def _criar_testes():
    for nome in EDITAIS:
        for secao in SECOES_SEM_PDF + SECOES_COM_PDF:
            def teste(self, nome=nome, secao=secao):
                self._comparar(nome, secao)
            teste.__doc__ = f'[{nome}] seção "{secao}" idêntica ao golden.'
            setattr(TestRegressaoGolden,
                    f'test_{nome}_{secao.replace("-", "_")}', teste)


_criar_testes()

if __name__ == '__main__':
    unittest.main()
