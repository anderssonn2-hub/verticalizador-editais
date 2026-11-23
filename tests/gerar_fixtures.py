"""Gera fixtures de texto e snapshots golden a partir dos PDFs de referência.

Uso (a partir da raiz do projeto):
    .venv\\Scripts\\python.exe -m tests.gerar_fixtures

- Fixtures: tests/fixtures/<edital>/pagina_NNN.txt (texto por página, mesmo
  leitor do Raio-X: leitura_pdf.ler, com OCR quando necessário).
- Golden:   tests/golden/<edital>.json (comportamento atual congelado).

Regerar fixtures/golden só deve acontecer de forma consciente, pois redefine
o contrato de regressão.
"""
import hashlib
import json
import sys

from tests.util import EDITAIS, FIXTURES, GOLDEN, caminho_pdf, PROJETO

if str(PROJETO) not in sys.path:
    sys.path.insert(0, str(PROJETO))


def gerar(nome):
    pdf = caminho_pdf(nome)
    if not pdf.is_file():
        print(f'[{nome}] PDF ausente: {pdf} — pulado.')
        return False

    from leitura_pdf import ler
    data = pdf.read_bytes()
    print(f'[{nome}] lendo {pdf.name} …')
    pgs, ocr = ler(data)

    pasta = FIXTURES / nome
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob('pagina_*.txt'):
        antigo.unlink()
    for i, texto in enumerate(pgs, 1):
        with open(pasta / f'pagina_{i:03d}.txt', 'w',
                  encoding='utf-8', newline='') as f:
            f.write(texto)

    meta = {
        'pdf': pdf.name,
        'sha256_pdf': hashlib.sha256(data).hexdigest(),
        'n_paginas': len(pgs),
        'paginas_ocr': ocr,
        'leitor': 'leitura_pdf.ler',
    }
    with open(pasta / 'meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f'[{nome}] {len(pgs)} páginas salvas (OCR em {len(ocr)}).')

    from tests.pipeline_atual import executar
    snapshot = executar(pgs, data)
    GOLDEN.mkdir(parents=True, exist_ok=True)
    with open(GOLDEN / f'{nome}.json', 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"[{nome}] golden salvo: {len(snapshot['cargos'])} cargos, "
          f"{len(snapshot['blocos'])} blocos de conteúdo.")
    return True


if __name__ == '__main__':
    ok = [n for n in EDITAIS if gerar(n)]
    print('Concluído para:', ', '.join(ok) if ok else 'nenhum edital.')
