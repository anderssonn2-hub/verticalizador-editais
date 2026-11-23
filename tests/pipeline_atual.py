"""Espelho fiel do fluxo de extração do raio_x.py (V3.0.11 DEV).

Este módulo NÃO altera a produção: ele reproduz, passo a passo, as mesmas
chamadas que `raio_x.mostrar_raio_x` faz, para que os testes de regressão
possam congelar o comportamento atual sem depender do Streamlit.

Qualquer divergência futura entre este espelho e raio_x.py deve ser tratada
como atualização consciente do contrato de regressão.
"""
import re

from tests.util import sha1, preparar_json


def executar(pgs, pdf_bytes=None):
    """Executa o pipeline atual e devolve um snapshot serializável."""
    from universal import localizar, cargos as cargos_cabecalho
    from identificador import identificar, chave
    from consolidar import consolidar, calendario
    from estrutura import opcoes, campos_extra
    from cronograma import tabela_datas
    from conteudo import parse, selected
    from cargo_dados import (
        extrair_dados, prova_por_cargo, complementar_dados_cargo_unico,
    )

    start, end = localizar(pgs)

    # --- identificação de cargos (mesma ordem do raio_x.py) ---
    nomes, campos = identificar(pgs)
    for nome in cargos_cabecalho(pgs):
        if chave(nome) not in {chave(x['Cargo']) for x in nomes}:
            nomes.append({'Cargo': nome, 'Página': None,
                          'Trecho': 'Cabeçalho detectado'})
    nomes, campos = consolidar(nomes, campos)

    blocks, detected = parse(pgs)
    opts = detected or opcoes(pgs)
    if blocks:
        source_pages = [p for b in blocks for p, _ in b['parts']]
        if source_pages:
            start, end = min(source_pages), max(source_pages)
    if opts:
        nomes = [dict(Cargo=x, Página=start,
                      Trecho='Cabeçalho do conteúdo programático')
                 for x in opts]

    # Dedup 1 (idêntico ao raio_x.py V3.0.11)
    cargos_unicos = {}
    for item in nomes:
        ident = chave(item['Cargo'].strip())
        if ident not in cargos_unicos:
            cargos_unicos[ident] = item
    nomes = list(cargos_unicos.values())

    campos += campos_extra(pgs)

    # Dedup 2 (o raio_x repete a deduplicação antes dos cartões)
    nomes_filtrados = []
    chaves_vistas = set()
    for item in nomes:
        codigo_nome = chave(item['Cargo'].strip())
        if codigo_nome in chaves_vistas:
            continue
        chaves_vistas.add(codigo_nome)
        nomes_filtrados.append(item)
    nomes = nomes_filtrados
    lista = [item['Cargo'] for item in nomes]

    # --- dados por cargo ---
    dados = extrair_dados(pgs, lista)
    dados = complementar_dados_cargo_unico(pgs, dados)

    vagas_tab = None
    if pdf_bytes is not None:
        from vagas_tabelas import extrair_vagas_tabelas
        vagas_tab = extrair_vagas_tabelas(pdf_bytes)
        for nome_cargo in lista:
            codigo_encontrado = re.match(r'^\s*(\d{1,4})\s*[-–—.:)]',
                                         nome_cargo)
            if not codigo_encontrado:
                continue
            registro = vagas_tab.get(codigo_encontrado.group(1))
            if registro and dados[nome_cargo].get('vagas') is None:
                dados[nome_cargo]['vagas'] = registro['vagas']
                dados[nome_cargo]['paginas'].add(registro['pagina'])

    identificacao = {
        campo: list(dict.fromkeys(
            x['Valor'] for x in campos if x['Campo'] == campo))
        for campo in ['Órgão', 'Banca']
    }

    # --- cronograma (tabela + fallback, como no raio_x) ---
    relevantes = tabela_datas(pgs)
    fallback = calendario(pgs)
    existentes = {r['Evento'] for r in relevantes}
    relevantes = relevantes + [r for r in fallback
                               if r['Evento'] not in existentes]

    # --- estrutura da prova e conteúdo por cargo ---
    prova = {c: prova_por_cargo(pgs, dados[c]['codigo']) for c in lista}
    conteudo_por_cargo = {c: selected(blocks, c) for c in lista}

    return {
        'n_paginas': len(pgs),
        'intervalo_conteudo': [start, end],
        'cargos': lista,
        'identificacao': identificacao,
        'dados': {c: _resumo_dados(dados[c]) for c in lista},
        'vagas_tabelas': preparar_json(vagas_tab) if vagas_tab is not None
        else None,
        'cronograma': preparar_json(relevantes),
        'prova': preparar_json(prova),
        'blocos': _resumo_blocos(blocks),
        'conteudo': {c: _resumo_selected(conteudo_por_cargo[c])
                     for c in lista},
        'cobertura_linhas': _cobertura_linhas(pgs, blocks, start, end),
    }


def _resumo_dados(d):
    return {
        'salario': d.get('salario'),
        'taxa': d.get('taxa'),
        'vagas': d.get('vagas'),
        'jornada': d.get('jornada'),
        'codigo': d.get('codigo'),
        'paginas': sorted(d.get('paginas') or []),
    }


def _resumo_blocos(blocks):
    out = []
    for b in blocks:
        texto = '\n'.join(f'{p}\t{l}' for p, l in b['parts'])
        out.append({
            'Grupo': b.get('Grupo'),
            'Disciplina': b.get('Disciplina'),
            'scope': list(b.get('scope') or []),
            'scope_codes': (list(b['scope_codes'])
                            if 'scope_codes' in b else None),
            'n_partes': len(b['parts']),
            'paginas': sorted({p for p, _ in b['parts']}),
            'sha1_texto': sha1(texto),
        })
    return out


def _resumo_selected(cards):
    out = []
    for r in cards:
        assuntos = r.get('Assuntos') or []
        out.append({
            'Grupo': r.get('Grupo'),
            'Disciplina': r.get('Disciplina'),
            'n_assuntos': len(assuntos),
            'paginas': r.get('Páginas'),
            'sha1_assuntos': sha1('\n'.join(assuntos)),
        })
    return out


def _cobertura_linhas(pgs, blocks, start, end):
    """Métricas para detectar perda de linhas em refatorações futuras."""
    from conteudo import clean
    linhas_em_blocos = sum(len(b['parts']) for b in blocks)
    linhas_limpas_secao = 0
    for p in pgs[start - 1:end]:
        for raw in p.splitlines():
            l = raw.strip()
            if l and clean(l):
                linhas_limpas_secao += 1
    return {
        'linhas_em_blocos': linhas_em_blocos,
        'linhas_limpas_secao': linhas_limpas_secao,
    }
