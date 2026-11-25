import re
from difflib import SequenceMatcher
from identificador import chave

G='Conhecimentos gerais'; E='Conhecimentos específicos'; U='Classificação não identificada'
CARGO=re.compile(r'^(?:\d{1,3}\s*[-–—]?\s*)?(?:cargo\s+de\s+)?(?:analista|tecnico)\s*,?\s+judiciario\b',re.I)
def canon(s):
    s=chave(s); s=re.sub(r'[^a-z0-9]+',' ',s).strip()
    s=re.sub(r'^(?:\d+ )?(?:cargo de )?','',s)
    s=re.sub(r'\b(?:trf\d+|jf[a-z]{2}|jesp)\b',' ',s)
    s=re.sub(r'\b(?:sem especialidade|de|da|do|especialidade)\b',' ',s)
    return ' '.join(s.split())
def matches(a,b):
    ca=re.match(r'^\s*(\d{1,3})\b',a); cb=re.match(r'^\s*(\d{1,3})\b',b)
    if ca and cb: return ca[1]==cb[1]
    a,b=canon(a),canon(b)
    return bool(a and b and (a==b or abs(len(a)-len(b))<=5 and SequenceMatcher(None,a,b).ratio()>=.94))
def clean(l):
    n=chave(l).strip()
    return not (not n or n.isdigit() or re.match(r'^(diario oficial da uniao|este documento pode|documento assinado|www\s*\.|pcimarkpci)',n))
def heading(l):
    n=chave(l).strip()
    return re.match(r'^(?:anexo\s+[ivxlcd\d|]+\s*[-–—:]?\s*)?(?:conteudos? programaticos?|programa de provas|objetos de avaliacao)\s*[:.]?$',n)
def parse(pgs):
    active=False; group=U; scope=[]; blocks=[]; cargo_list=[]; current=None; pending=None; blank=True; shared=False
    def flush():
        nonlocal current
        if current and current['parts']: blocks.append(current)
        current=None
    for page,p in enumerate(pgs,1):
        for raw in p.splitlines():
            l=raw.strip(); n=chave(l)
            if heading(l): active=True; blank=True; continue
            if not active: continue
            if re.match(r'^anexo\s+[ivxlcd\d|]+\b',n): flush(); return blocks,cargo_list
            if not clean(l):
                if not l: blank=True
                continue
            if re.match(r'^para os cargos? de\b',n):
                flush(); pending=l; scope=[]; blank=True; continue
            gm=re.match(r'^conhecimentos\s+(gerais|basicos|especificos)\b',n)
            if gm:
                flush(); shared=False; group=E if gm[1]=='especificos' else G
                if pending:
                    scope=[x.strip(' ,:-') for x in re.split(r'(?=\b(?:Analista|Técnico)\s+Judiciário)',pending,flags=re.I) if CARGO.match(chave(x.strip()))]; pending=None
                elif group==G: scope=[] if 'todos' in n and 'tecnic' not in n and 'exceto' not in n else [l] if len(n)>25 else []
                else: scope=[]
                blank=True; continue
            if pending is not None: pending+=' '+l; continue
            if CARGO.match(n):
                flush()
                if group==E:
                    name=l.strip(' ,;:'); name=re.sub(r'\s+e$','',name,flags=re.I)
                    if not any(matches(name,x) for x in cargo_list): cargo_list.append(name)
                    scope=scope+[name] if shared else [name]
                    shared=n.endswith(' e')
                elif scope and 'exceto' in chave(scope[0]): scope.append(l)
                blank=True; continue
            if re.match(r'^ensino\s+(superior|medio|fundamental)',n): continue
            if group==U: continue
            # Prefer paragraph beginnings, not colons embedded in wrapped topics.
            m=re.match(r'^([^:]{3,105}):\s*(.*)$',l) if blank or current is None else None
            if m and not re.search(r'[.;!?]|\b(?:lei n|artigos? \d)\b',chave(m[1])):
                flush(); current=dict(Grupo=group,scope=scope.copy(),Disciplina=m[1].strip(),parts=[]); l=m[2]
            elif (blank or current is None) and re.match(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ /-]{3,90}\s+(?=[A-ZÁÉÍÓÚ][a-z])',l):
                m=re.match(r'^([A-ZÁÉÍÓÚÂÊÔÃÕÇ /-]{3,90}?)\s+(?=[A-ZÁÉÍÓÚ][a-z])(.*)$',l)
                if m: flush(); current=dict(Grupo=group,scope=scope.copy(),Disciplina=m[1],parts=[]); l=m[2]
            if current is None: current=dict(Grupo=group,scope=scope.copy(),Disciplina='Disciplina não identificada',parts=[])
            if l: current['parts'].append((page,l))
            blank=False
    flush(); return blocks,cargo_list

def selected(blocks,cargo):
    out=[]
    for b in blocks:
        s=b['scope']; g=b['Grupo']
        if g==E and not s: continue
        if s:
            n=chave(s[0]); ok=any(matches(cargo,x) for x in s)
            if 'exceto' in n: ok=not any(matches(cargo,x) for x in s[1:]) if len(s)>1 else False
            elif 'todos' in n and 'tecnic' in n: ok='tecnico' in chave(cargo)
            if not ok: continue
        text=' '.join(t for _,t in b['parts']); pages=', '.join(map(str,sorted({p for p,_ in b['parts']})))
        # Split only clear sentence endings, preserving punctuation and nested semicolons.
        topics=re.split(r'(?<!\bnº)(?<!\bArt)(?<!\bart)(?<!\bInc)(?<=\.)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])',text)
        out.append(dict(Grupo=g,Disciplina=b['Disciplina'],Assuntos=topics,Páginas=pages))
    return out


# V3.0.11 - disciplinas numeradas
# Parser complementar para editais que apresentam:
# 1. DISCIPLINA
# 1.1 Assunto. 1.1.1 Subassunto.

_TITULO_NUMERADO = re.compile(
    r"^\s*(\d{1,2})\.\s+"
    r"([^\W\d_][\w\s,/()\-]*)"
    r"\s*$"
)

_TOPICO_NUMERADO = re.compile(
    r"(?<![\w.])(\d{1,2}(?:\.\d{1,3}){1,8})\.?"
    r"""(?=\s+(?:[^\W\d_]|["'(]))"""
)

def _parse_numerado(pgs):
    blocos = []
    atual = None
    grupo = None
    cargo = None
    ativo = False

    def fechar():
        nonlocal atual
        if atual and atual["parts"]:
            blocos.append(atual)
        atual = None

    titulo_re = re.compile(
        r"^\s*(\d{1,2})\.\s+(.+?)\s*$"
    )

    for pagina, texto in enumerate(pgs, 1):
        for linha in texto.splitlines():
            linha = linha.strip()
            if not linha:
                continue

            normal = chave(linha)

            if heading(linha):
                ativo = True
                continue

            if not ativo:
                continue

            if re.match(r"^conhecimentos\s+(basicos|gerais|especificos)\b", normal):
                fechar()
                grupo = E if "especificos" in normal else G
                continue

            if grupo is None:
                if re.match(
                    r"^(?:investigador|delegado|escrivao|perito|agente|papiloscopista)\b",
                    normal
                ):
                    cargo = linha
                continue

            if re.match(r"^anexo\s+[ivxlcd\d]+\b", normal):
                fechar()
                return blocos, cargo

            titulo = titulo_re.match(linha)

            if titulo and titulo.group(2).upper() == titulo.group(2) and len(titulo.group(2)) >= 5:
                fechar()
                atual = {
                    "Grupo": grupo,
                    "scope": [cargo] if cargo else [],
                    "Disciplina": titulo.group(2).strip(),
                    "parts": [],
                }
                continue

            if atual is not None and clean(linha):
                atual["parts"].append((pagina, linha))

    fechar()
    return (blocos, cargo) if len(blocos) >= 2 else ([], None)


def _assuntos_numerados(partes):
    texto = " ".join(linha for _, linha in partes)
    texto = re.sub(r"\s+", " ", texto).strip()

    if not texto:
        return []

    # Reconhece tópicos que começam com numeração hierárquica,
    # mas evita vers?es precedidas por nomes de aplicativos.
    padrao = _TOPICO_NUMERADO

    marcadores = []

    for m in padrao.finditer(texto):
        antes = texto[max(0, m.start()-25):m.start()].lower()

        if re.search(
            r"(?:libreoffice|office|windows|chrome)\s*$",
            antes
        ):
            continue

        marcadores.append(m)

    if not marcadores:
        return [texto]

    assuntos = []

    for indice, marcador in enumerate(marcadores):
        inicio = marcador.start()
        fim = (
            marcadores[indice + 1].start()
            if indice + 1 < len(marcadores)
            else len(texto)
        )
        trecho = texto[inicio:fim].strip(" ;")
        if trecho:
            assuntos.append(trecho)

    return assuntos


_parse_anterior = parse
_selected_anterior = selected


def parse(pgs):
    blocos, cargo = _parse_numerado(pgs)

    if blocos:
        cargos = [cargo] if cargo else []
        return blocos, cargos

    return _parse_anterior(pgs)


def selected(blocks, cargo):
    if not blocks:
        return []

    if not all("parts" in bloco for bloco in blocks):
        return _selected_anterior(blocks, cargo)

    resultado = []

    for bloco in blocks:
        escopo = bloco.get("scope", [])

        if escopo and not any(matches(cargo, nome) for nome in escopo):
            continue

        partes = bloco["parts"]
        paginas = sorted({pagina for pagina, _ in partes})

        resultado.append({
            "Grupo": bloco["Grupo"],
            "Disciplina": bloco["Disciplina"],
            "Assuntos": _assuntos_numerados(partes),
            "Páginas": ", ".join(map(str, paginas)),
        })

    return resultado



# V3.0.11 - associacao universal de grupos de cargos
# Camada complementar: preserva os extratores existentes.

import unicodedata as _unicode_grupos


def _normal_grupos(valor):
    valor = _unicode_grupos.normalize("NFKD", str(valor or ""))
    valor = "".join(
        c for c in valor if not _unicode_grupos.combining(c)
    )
    return re.sub(r"\s+", " ", valor).casefold().strip()


def _codigo_grupos(cargo):
    encontrado = re.match(r"^\s*(\d{1,4})\s*[-–—.:)]", cargo)
    return encontrado.group(1) if encontrado else None


def _cabecalho_grupos(linha):
    normal = _normal_grupos(linha)
    return bool(re.match(
        r"^conhecimentos?\s+(?:gerais|basicos)"
        r"\s+para\s+(?:os?\s+)?"
        r"(?:cargos?|cargos/areas/especialidades)"
        r"\s*:",
        normal
    ))


def _disciplina_grupos(linha):
    # Titulo de disciplina seguido por dois-pontos.
    # Evita tratar descricoes longas como titulos.
    encontrado = re.match(r"^\s*([^:]{3,75}):\s*(.*)$", linha)
    if not encontrado:
        return None

    titulo = encontrado.group(1).strip()

    if len(titulo.split()) > 9:
        return None

    normal = _normal_grupos(titulo)

    if re.search(
        r"\b(?:lei|decreto|resolucao|artigo|inciso)\s+"
        r"(?:n[o.]?\s*)?\d",
        normal
    ):
        return None

    return titulo, encontrado.group(2)


def _extrair_grupos_gerais(pgs):
    """
    Detecta secoes de conhecimentos gerais com lista explicita
    de cargos identificados por codigo.
    """
    resultado = []
    ativo = False
    lendo_cargos = False
    codigos = set()
    atual = None

    def fechar():
        nonlocal atual
        if atual and atual["parts"] and codigos:
            atual["scope_codes"] = sorted(codigos)
            resultado.append(atual)
        atual = None

    for pagina, texto in enumerate(pgs, 1):
        for linha_original in texto.splitlines():
            linha = linha_original.strip()
            if not linha:
                continue

            normal = _normal_grupos(linha)

            if _cabecalho_grupos(linha):
                fechar()
                ativo = True
                lendo_cargos = True
                codigos = set()

                # Pode haver codigo na propria linha do cabecalho.
                depois = linha.split(":", 1)[-1]
                for codigo in re.findall(
                    r"(?:^|[,;]|\be\s+)\s*(\d{1,4})\s*[-–—]",
                    depois,
                    flags=re.I
                ):
                    codigos.add(codigo)

                continue

            if not ativo:
                continue

            if re.match(
                r"^conhecimentos?\s+especificos\b",
                normal
            ):
                fechar()
                ativo = False
                lendo_cargos = False
                continue

            if re.match(r"^anexo\s+[ivxlcdm\d]+\b", normal):
                fechar()
                ativo = False
                lendo_cargos = False
                continue

            if lendo_cargos:
                disciplina = _disciplina_grupos(linha)

                if disciplina and codigos:
                    lendo_cargos = False
                else:
                    # Os codigos aparecem antes dos nomes dos cargos.
                    # Aceita separadores variados e linhas quebradas.
                    for codigo in re.findall(
                        r"(?:^|[,;]|\be\s+)\s*"
                        r"(\d{1,4})\s*[-–—]",
                        linha,
                        flags=re.I
                    ):
                        codigos.add(codigo)

                    continue

            disciplina = _disciplina_grupos(linha)

            if disciplina:
                fechar()
                titulo, corpo = disciplina
                atual = {
                    "Grupo": G,
                    "Disciplina": titulo,
                    "scope": [],
                    "parts": []
                }
                if corpo:
                    atual["parts"].append((pagina, corpo))

            elif atual is not None:
                atual["parts"].append((pagina, linha))

    fechar()
    return resultado


_parse_v311_anterior = parse
_selected_v311_anterior = selected


def parse(pgs):
    blocos, cargos = _parse_v311_anterior(pgs)

    gerais_novos = _extrair_grupos_gerais(pgs)

    if not gerais_novos:
        return blocos, cargos

    # Substitui apenas os conhecimentos gerais quando a
    # associacao por codigos foi identificada.
    especificos = [
        bloco for bloco in blocos
        if bloco.get("Grupo") != G
    ]

    return gerais_novos + especificos, cargos


def selected(blocks, cargo):
    codigo = _codigo_grupos(cargo)

    com_codigos = [
        bloco for bloco in blocks
        if "scope_codes" in bloco
    ]

    tradicionais = [
        bloco for bloco in blocks
        if "scope_codes" not in bloco
    ]

    resultado = _selected_v311_anterior(tradicionais, cargo)

    for bloco in com_codigos:
        if codigo not in bloco["scope_codes"]:
            continue

        partes = bloco["parts"]
        paginas = sorted({p for p, _ in partes})

        resultado.append({
            "Grupo": bloco["Grupo"],
            "Disciplina": bloco["Disciplina"],
            "Assuntos": _assuntos_numerados(partes),
            "Páginas": ", ".join(map(str, paginas))
        })

    return resultado



# V3.0.11 - consolidacao de disciplinas gerais

from collections import Counter as _CounterDisciplinas



def _consolidar_disciplinas_gerais(blocos):
    """Consolida continuacoes sem descartar texto ou paginas."""
    gerais = [
        b for b in blocos
        if b.get("Grupo") == G and "scope_codes" in b
    ]

    if not gerais:
        return blocos

    frequencias = _CounterDisciplinas(
        _normal_grupos(b["Disciplina"]) for b in gerais
    )

    resultado = []
    anterior = None

    for bloco in gerais:
        titulo = bloco["Disciplina"]
        normal = _normal_grupos(titulo)
        mesmo_grupo = (
            anterior is not None
            and anterior["scope_codes"] == bloco["scope_codes"]
        )

        ultima = ""
        if mesmo_grupo and anterior["parts"]:
            ultima = anterior["parts"][-1][1].strip()

        ultima_palavra = (
            _normal_grupos(ultima).split()[-1]
            if ultima.strip() else ""
        )

        # Uma linha terminada por conectivo ou preposicao
        # indica que a proxima linha continua o assunto.
        continua_frase = ultima_palavra in {
            "e", "ou", "de", "da", "do", "dos", "das",
            "em", "para", "com", "sobre"
        }

        titulo_valido = (
            frequencias[normal] >= 2
            and bool(titulo)
            and titulo[0].isupper()
            and not any(c.isdigit() for c in titulo)
            and not any(c in titulo for c in (";", ")", ".", "/"))
            and not continua_frase
        )

        if anterior is None or not mesmo_grupo or titulo_valido:
            novo = dict(bloco)
            novo["parts"] = list(bloco["parts"])
            resultado.append(novo)
            anterior = novo
            continue

        # Recupera o titulo falso como parte do texto original.
        partes = bloco["parts"]
        if partes:
            pagina = partes[0][0]
            anterior["parts"].append((pagina, titulo + ":"))
            anterior["parts"].extend(partes)

    outros = [
        b for b in blocos
        if not (
            b.get("Grupo") == G
            and "scope_codes" in b
        )
    ]

    return resultado + outros


_parse_antes_consolidacao = parse


def parse(pgs):
    blocos, cargos = _parse_antes_consolidacao(pgs)
    return _consolidar_disciplinas_gerais(blocos), cargos


# V3.0.11 - refinamento estrutural de titulos (revisao 4)
_parse_antes_segmentacao_segura = parse

def _segmentar_sem_perder_linhas(blocos):
    """Divide somente titulos com estrutura de disciplina; nao altera parts."""
    import re
    from collections import Counter
    candidatos = []
    frequencias = Counter()
    for b in blocos:
        if b.get('Grupo') != E:
            continue
        for i, (pagina, linha) in enumerate(b['parts']):
            if not i:
                continue
            m = re.match(r'^([^:]{3,80}):\s+(.+)$', linha)
            if not m:
                continue
            titulo = m.group(1).strip()
            anterior = b['parts'][i - 1][1].strip()
            if (len(titulo.split()) > 9 or len(titulo) > 70
                or not titulo[0].isupper()
                or re.search(r'[.;()\d/]', titulo)
                or not anterior.endswith(('.', '!', '?'))):
                continue
            normal = _normal_grupos(titulo)
            palavras = normal.split()
            # Titulos que comecam por artigo/preposicao sao tipicamente
            # continuacoes de assunto ("Das funcoes...", "Do salario...").
            if not palavras or palavras[0] in {
                'o', 'a', 'os', 'as', 'do', 'da', 'dos', 'das',
                'de', 'em', 'no', 'na', 'nos', 'nas', 'sobre', 'para'
            }:
                continue
            frequencias[normal] += 1
            candidatos.append((id(b), i, titulo, normal))
    cortes = {}
    for bid, i, titulo, normal in candidatos:
        formal = bool(re.match(
            r'^(?:nocoes? de (?:direito |administracao |orcamento |gestao )|'
            r'direito (?:constitucional|administrativo|do trabalho|processual|civil|penal)|'
            r'contabilidade (?:geral|aplicada)|orcamento publico|'
            r'administracao financeira e orcamentaria)$', normal))
        if formal or frequencias[normal] >= 2:
            cortes.setdefault(bid, {})[i] = titulo
    resultado = []
    for b in blocos:
        posicoes = cortes.get(id(b), {})
        if not posicoes:
            resultado.append(b)
            continue
        atual = dict(b)
        atual['parts'] = []
        for i, item in enumerate(b['parts']):
            if i in posicoes:
                if atual['parts']:
                    resultado.append(atual)
                atual = dict(b)
                atual['Disciplina'] = posicoes[i]
                atual['parts'] = []
            atual['parts'].append(item)
        if atual['parts']:
            resultado.append(atual)
    return resultado

def parse(pgs):
    blocos, cargos = _parse_antes_segmentacao_segura(pgs)
    return _segmentar_sem_perder_linhas(blocos), cargos


# V3.0.11 - continuidade de titulos entre paginas (revisao 5)
_parse_antes_continuacoes = parse

def _unir_titulos_quebrados_entre_paginas(blocos):
    """Une falsos titulos de pagina sem remover nem reordenar linhas originais."""
    import re
    resultado = []
    for bloco in blocos:
        if bloco.get('Grupo') != E or not resultado or not bloco.get('parts'):
            resultado.append(bloco)
            continue
        anterior = resultado[-1]
        titulo = str(bloco.get('Disciplina', '')).strip()
        partes_anteriores = anterior.get('parts') or []
        if (anterior.get('Grupo') != E or not partes_anteriores
            or anterior.get('scope') != bloco.get('scope')
            or anterior.get('scope_codes') != bloco.get('scope_codes')):
            resultado.append(bloco)
            continue
        pag_anterior, linha_anterior = partes_anteriores[-1]
        pag_atual = bloco['parts'][0][0]
        texto_anterior = str(linha_anterior).rstrip()
        # Somente sequencias de paginas consecutivas e frases inacabadas.
        if not (isinstance(pag_anterior, int) and isinstance(pag_atual, int)
                and pag_atual == pag_anterior + 1
                and texto_anterior and not texto_anterior.endswith(('.', ';', ':', '!', '?'))):
            resultado.append(bloco)
            continue
        # Fragmentos que iniciam em minuscula ou numero de norma, sem assumir edital.
        fragmento = bool(re.match(r'^[a-zà-ÿ]', titulo)) or bool(
            re.match(r'^\d{3,}(?:\s|\s*[–-])', titulo))
        if not fragmento or len(titulo) > 85:
            resultado.append(bloco)
            continue
        # O parser anterior retirou o titulo da linha; reinseri-lo na pagina original.
        # Nao altera nem remove nenhuma das linhas que ja estavam em parts.
        anterior['parts'].append((pag_atual, titulo + ':'))
        anterior['parts'].extend(bloco['parts'])
    return resultado

def parse(pgs):
    blocos, cargos = _parse_antes_continuacoes(pgs)
    return _unir_titulos_quebrados_entre_paginas(blocos), cargos
