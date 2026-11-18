import re
from datetime import datetime

def classificar(rows):
    out=[]
    for r in rows:
        t=r['Trecho']; evento='Outras datas — conferir'
        # O contexto é indicativo; referências legais não são prazos.
        if re.search(r'\b(?:lei|decreto|resolução|portaria)\s+(?:n[.º°o]*\s*)?\d',t,re.I): evento='Referência normativa / contexto misto'
        elif re.search(r'inscriç',t,re.I): evento='Inscrições'
        elif re.search(r'prova\s+(?:objetiva|escrita|discursiva)|aplicação das provas',t,re.I): evento='Possível data de prova'
        elif re.search(r'isenção',t,re.I): evento='Isenção'
        elif re.search(r'recurso',t,re.I): evento='Recursos'
        elif re.search(r'resultado|gabarito',t,re.I): evento='Resultado / gabarito'
        out.append({'Evento':evento,**r})
    return out

# V3.0.9: eventos delimitados por linha/linha numerada, inclusive em continuação.
from identificador import chave
from extrator_raiox import DATA, MESES

PROVA = re.compile(r'\b(?:(?:aplicacao|realizacao|data(?:\s+(?:prevista|provavel))?)\s+(?:(?:da|das|de)\s+)?provas?|provas?\s+(?:objetivas?|escritas?|discursivas?)\s*(?::|$))\b')
EXCLUI = re.compile(r'\b(?:gabarito|convocacao|recurso|resultado|pagamento|isencao|publicacao|divulgacao|local|locais|prazo)\b')

def tabela_datas(pgs):
    out = {}; ativo = False
    def processar(linhas):
        if not linhas: return
        texto = ' '.join(l for _,l in linhas); n=chave(texto)
        if EXCLUI.search(n): return
        inscr = re.search(r'\bperiodo (?:de|das) inscri',n)
        prova = PROVA.search(n)
        if not (inscr or prova): return
        ds=[]
        for m in DATA.finditer(texto):
            try:
                dt=datetime(int(m[3]),int(m[2]),int(m[1])) if m[1] else datetime(int(m[6]),MESES.index(m[5].lower())+1,int(m[4]))
            except ValueError: continue
            ds.append((m,dt))
        if not ds:return
        def add(event,dt):
            s=dt.strftime('%d/%m/%Y'); out.setdefault((event,s),dict(Evento=event,Data=s,Página=linhas[0][0],Trecho=texto))
        if inscr:
            if len(ds)>=2: add('Início das inscrições',ds[0][1]);add('Encerramento das inscrições',ds[-1][1])
            else:
                m,dt=ds[0]; prefix=texto[:m.start()]
                a=re.search(r'\b(\d{1,2})/(\d{1,2})\s*(?:a|até|–|-)\s*$',prefix,re.I)
                if a:
                    try:
                        mes=int(a[2]); ini=datetime(dt.year-(mes>dt.month),mes,int(a[1]))
                        if ini<=dt:add('Início das inscrições',ini);add('Encerramento das inscrições',dt)
                    except ValueError: pass
        elif prova:
            for _,dt in ds:add('Data prevista da prova',dt)
    row=[]
    for page,raw in enumerate(pgs,1):
        for line in raw.splitlines():
            line=line.strip(); n=chave(line)
            if not line:continue
            if re.search(r'\bcronograma\b',n) and not re.search(r'sujeito|alterac|conforme|previsto no',n) and len(n)<130:
                processar(row);row=[];ativo=True;continue
            if not ativo:continue
            if re.match(r'^anexo\s+[ivxlcd\d]+\b',n) or 'cronograma sujeito' in n:
                processar(row);row=[];ativo=False;continue
            if re.search(r'diario oficial da uniao|documento assinado digitalmente|este documento pode ser verificado|pciconcursos|in.gov.br/autenticidade|issn ',n):continue
            if re.match(r'^\d{1,3}[.)]?\s+(?=[a-z])',n) or re.match(r'^(?:periodo de|aplicacao|realizacao|data|publicacao|divulgacao|convocacao|vencimento|resultado)\b',n):
                processar(row);row=[(page,line)]
            elif row:row.append((page,line))
    processar(row)
    return list(out.values())
