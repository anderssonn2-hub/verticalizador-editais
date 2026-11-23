"""Invariantes universais do extrator (valem para qualquer edital).

Detectam perda de linhas, páginas fora do documento e associação incorreta
entre cargos e blocos de conteúdo. Testes marcados com expectedFailure
documentam DEFEITOS CONHECIDOS do estado atual — não devem ser "corrigidos"
no teste, e sim no código, em etapa futura autorizada.
"""
import re
import unittest

from tests.util import EDITAIS, tem_fixtures, carregar_paginas

DISPONIVEIS = [n for n in EDITAIS if tem_fixtures(n)]

_cache = {}


def _contexto(nome):
    """parse/selected reais sobre as fixtures (sem golden)."""
    if nome not in _cache:
        from conteudo import parse, selected
        from universal import localizar
        pgs = carregar_paginas(nome)
        blocks, detected = parse(pgs)
        start, end = localizar(pgs)
        if blocks:
            src = [p for b in blocks for p, _ in b['parts']]
            if src:
                start, end = min(src), max(src)
        _cache[nome] = dict(pgs=pgs, blocks=blocks, detected=detected,
                            start=start, end=end)
    return _cache[nome]


def _lista_cargos(nome):
    from tests.pipeline_atual import executar
    ctx = _contexto(nome)
    chave_lista = 'lista_' + nome
    if chave_lista not in _cache:
        _cache[chave_lista] = executar(ctx['pgs'])['cargos']
    return _cache[chave_lista]


class TestInvariantes(unittest.TestCase):

    def _cada_edital(self):
        if not DISPONIVEIS:
            self.skipTest('Nenhuma fixture disponível em tests/fixtures/.')
        for nome in DISPONIVEIS:
            yield nome, _contexto(nome)

    def test_paginas_dos_blocos_dentro_do_documento(self):
        """Nenhum bloco referencia página inexistente no PDF."""
        for nome, ctx in self._cada_edital():
            n = len(ctx['pgs'])
            for b in ctx['blocks']:
                for p, _ in b['parts']:
                    with self.subTest(edital=nome, disciplina=b['Disciplina']):
                        self.assertTrue(1 <= p <= n,
                                        f'página {p} fora de 1..{n}')

    def test_blocos_nao_vazios(self):
        """Todo bloco publicado tem ao menos uma linha de conteúdo."""
        for nome, ctx in self._cada_edital():
            for b in ctx['blocks']:
                with self.subTest(edital=nome, disciplina=b['Disciplina']):
                    self.assertTrue(b['parts'], 'bloco sem partes')
                    self.assertTrue(
                        all(str(l).strip() for _, l in b['parts']),
                        'linha vazia dentro de bloco')

    def test_assuntos_nao_vazios(self):
        """selected() não devolve assuntos vazios."""
        from conteudo import selected
        for nome, ctx in self._cada_edital():
            for cargo in _lista_cargos(nome):
                for card in selected(ctx['blocks'], cargo):
                    with self.subTest(edital=nome, cargo=cargo,
                                      disciplina=card['Disciplina']):
                        self.assertTrue(card['Assuntos'],
                                        'cartão sem assuntos')
                        self.assertTrue(
                            all(a.strip() for a in card['Assuntos']),
                            'assunto vazio')

    def test_todo_cargo_recebe_gerais_e_especificos(self):
        """Associação cargo↔conteúdo: nenhum cargo fica sem um dos grupos.

        Se um cargo deixar de receber blocos gerais ou específicos após uma
        mudança, a associação regrediu.
        """
        from conteudo import selected, G, E
        for nome, ctx in self._cada_edital():
            grupos_existentes = {b.get('Grupo') for b in ctx['blocks']}
            for cargo in _lista_cargos(nome):
                cards = selected(ctx['blocks'], cargo)
                recebidos = {c['Grupo'] for c in cards}
                for grupo in (G, E):
                    if grupo not in grupos_existentes:
                        continue
                    with self.subTest(edital=nome, cargo=cargo, grupo=grupo):
                        self.assertIn(
                            grupo, recebidos,
                            f'cargo sem nenhum bloco de "{grupo}"')

    def test_associacao_por_codigo_respeita_scope_codes(self):
        """Blocos com scope_codes só chegam a cargos cujo código pertence
        à lista — nunca a cargos de outro código."""
        from conteudo import selected, _codigo_grupos
        from tests.util import sha1
        for nome, ctx in self._cada_edital():
            codificados = [b for b in ctx['blocks'] if 'scope_codes' in b]
            if not codificados:
                continue
            # Assinatura dos blocos codificados → códigos autorizados.
            autorizados = {}
            for b in codificados:
                sig = (b['Disciplina'],
                       sha1('\n'.join(l for _, l in b['parts'])))
                autorizados.setdefault(sig, set()).update(b['scope_codes'])
            assinaturas = set(autorizados)
            for cargo in _lista_cargos(nome):
                codigo = _codigo_grupos(cargo)
                cards = selected(ctx['blocks'], cargo)
                for b in codificados:
                    recebeu = any(c['Disciplina'] == b['Disciplina']
                                  for c in cards
                                  if c['Grupo'] == b['Grupo'])
                    if codigo not in b['scope_codes'] and recebeu:
                        # A disciplina pode vir de OUTRO bloco autorizado.
                        outros = [x for x in codificados
                                  if x is not b
                                  and x['Disciplina'] == b['Disciplina']
                                  and codigo in x['scope_codes']]
                        with self.subTest(edital=nome, cargo=cargo,
                                          disciplina=b['Disciplina']):
                            self.assertTrue(
                                outros,
                                'cargo recebeu bloco de códigos alheios '
                                f'{sorted(b["scope_codes"])[:8]}')
            del assinaturas  # documentação da estratégia

    def test_bloco_especifico_exige_escopo_compativel(self):
        """Blocos específicos com escopo nominal só chegam a cargos que
        casam com algum nome do escopo (oráculo: conteudo.matches)."""
        from conteudo import selected, matches, E, chave
        for nome, ctx in self._cada_edital():
            nominais = [b for b in ctx['blocks']
                        if b.get('Grupo') == E and b.get('scope')
                        and 'scope_codes' not in b]
            if not nominais:
                continue
            for cargo in _lista_cargos(nome):
                cards = {(c['Grupo'], c['Disciplina'])
                         for c in selected(ctx['blocks'], cargo)}
                for b in nominais:
                    if (E, b['Disciplina']) not in cards:
                        continue
                    escopo = b['scope']
                    n0 = chave(escopo[0])
                    if 'exceto' in n0 or 'todos' in n0:
                        continue
                    compativel = any(matches(cargo, s) for s in escopo)
                    alternativos = [x for x in nominais
                                    if x is not b
                                    and x['Disciplina'] == b['Disciplina']
                                    and any(matches(cargo, s)
                                            for s in x.get('scope') or [])]
                    with self.subTest(edital=nome, cargo=cargo,
                                      disciplina=b['Disciplina']):
                        self.assertTrue(
                            compativel or alternativos,
                            f'bloco com escopo {escopo[:2]} atribuído a '
                            f'cargo incompatível')

    @unittest.expectedFailure
    def test_nenhuma_linha_limpa_fica_fora_dos_blocos(self):
        """FALHA CONHECIDA (V3.0.11): o parser descarta linhas da seção de
        conteúdo programático sem rastro (grupo "não identificado",
        cabeçalhos intermediários e quebras de associação).

        Medido nas fixtures atuais: TRT4 ≈ 52 linhas e PCMG ≈ 17 linhas da
        seção não aparecem em nenhum bloco. Se este teste passar a dar
        "unexpected success", a cobertura total foi atingida e ele deve ser
        promovido a invariante obrigatório.
        """
        from conteudo import clean, heading, CARGO, chave
        estruturais = re.compile(
            r'^(?:conhecimentos\s+(?:gerais|basicos|especificos)\b'
            r'|para os cargos? de\b'
            r'|ensino\s+(?:superior|medio|fundamental)\b'
            r'|anexo\s+[ivxlcd\d]+\b)')
        faltantes = {}
        for nome, ctx in self._cada_edital():
            corpo_por_pagina = {}
            for b in ctx['blocks']:
                for p, l in b['parts']:
                    corpo_por_pagina.setdefault(p, []).append(
                        ' '.join(chave(l).split()))
            corpo_por_pagina = {p: ' \n'.join(v) + ' \n' + ' '.join(v)
                                for p, v in corpo_por_pagina.items()}
            perdidas = []
            for pagina in range(ctx['start'], ctx['end'] + 1):
                for raw in ctx['pgs'][pagina - 1].splitlines():
                    l = raw.strip()
                    if not l or not clean(l):
                        continue
                    n = ' '.join(chave(l).split())
                    if (heading(l) or estruturais.match(n)
                            or CARGO.match(chave(l))):
                        continue
                    vizinhas = ' '.join(
                        corpo_por_pagina.get(p, '')
                        for p in (pagina - 1, pagina, pagina + 1))
                    if n not in vizinhas:
                        perdidas.append((pagina, l[:80]))
            if perdidas:
                faltantes[nome] = perdidas
        self.assertFalse(
            faltantes,
            'Linhas da seção de conteúdo ausentes dos blocos: '
            + '; '.join(f'{k}: {len(v)} linha(s), ex.: {v[:3]}'
                        for k, v in faltantes.items()))


if __name__ == '__main__':
    unittest.main()
