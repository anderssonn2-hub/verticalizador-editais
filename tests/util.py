"""Utilitários dos testes: caminhos, fixtures e serialização.

Nenhuma lógica de produção é alterada por este pacote.
"""
import hashlib
import json
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJETO = TESTS_DIR.parent
FIXTURES = TESTS_DIR / 'fixtures'
GOLDEN = TESTS_DIR / 'golden'
PDFS = FIXTURES / 'pdfs'

if str(PROJETO) not in sys.path:
    sys.path.insert(0, str(PROJETO))

EDITAIS = ['trt4', 'pcmg']


def tem_fixtures(nome):
    pasta = FIXTURES / nome
    return pasta.is_dir() and any(pasta.glob('pagina_*.txt'))


def carregar_paginas(nome):
    """Carrega o texto das páginas a partir das fixtures (sem ler o PDF)."""
    pasta = FIXTURES / nome
    arquivos = sorted(pasta.glob('pagina_*.txt'))
    paginas = []
    for arq in arquivos:
        with open(arq, encoding='utf-8', newline='') as f:
            paginas.append(f.read())
    return paginas


def carregar_meta(nome):
    with open(FIXTURES / nome / 'meta.json', encoding='utf-8') as f:
        return json.load(f)


def carregar_golden(nome):
    with open(GOLDEN / f'{nome}.json', encoding='utf-8') as f:
        return json.load(f)


def caminho_pdf(nome):
    return PDFS / f'{nome}.pdf'


def sha1(texto):
    return hashlib.sha1(texto.encode('utf-8')).hexdigest()


def preparar_json(obj):
    """Converte sets e tuplas para formas serializáveis e determinísticas."""
    if isinstance(obj, dict):
        return {str(k): preparar_json(v) for k, v in obj.items()}
    if isinstance(obj, set):
        return sorted(preparar_json(x) for x in obj)
    if isinstance(obj, (list, tuple)):
        return [preparar_json(x) for x in obj]
    return obj
