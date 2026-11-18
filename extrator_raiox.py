import re
from datetime import date
MESES='janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro'.split()
DATA=re.compile(r'\b(?:(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})|(\d{1,2})(?:\s*\([^)]{1,40}\))?\s+de\s+('+'|'.join(MESES)+r')\s+de\s+(\d{4}))\b',re.I)
def analisar(pgs):
    datas=[]; candidatos=[]; questoes=[]; pesos=[]; vistos=set()
    for i,p in enumerate(pgs,1):
        texto=' '.join(p.split())
        for m in DATA.finditer(texto):
            try:
                d=date(int(m[3]),int(m[2]),int(m[1])) if m[1] else date(int(m[6]),MESES.index(m[5].lower())+1,int(m[4]))
            except ValueError: continue
            trecho=texto[max(0,m.start()-110):m.end()+65]
            datas.append({'Data':d.strftime('%d/%m/%Y'),'Página':i,'Trecho':trecho})
        if i<=12:
            for campo,pat in [('Cargo',r'\b(?:cargo|carreira)\s+de\s+([^.;\n,]{3,100})'),('Vagas',r'\b\d[\d.]*\s*(?:\([^)]{1,60}\)\s*)?vagas\b'),('Remuneração / taxa',r'R\$\s*[\d.]+,\d{2}'),('Banca / órgão',r'Fundação\s+Get[uú]lio\s+Vargas|Polícia\s+Civil\s+do\s+Estado\s+de\s+[^,.;\n]{3,50}')]:
                for m in re.finditer(pat,p,re.I):
                    trecho=' '.join(p[max(0,m.start()-60):m.end()+65].split())
                    key=(campo,m.group().casefold())
                    if key not in vistos:
                        vistos.add(key); candidatos.append({'Campo':campo,'Trecho':trecho,'Página':i})
        for m in re.finditer(r'(?im)^\s*(?:\d+[.)]\s*|[a-z]\)\s*)?(\d{1,3})\s+questões\s+de\s+([^;\n.]+)',p):
            questoes.append({'Disciplina':m[2].strip(),'Questões':int(m[1]),'Página':i})
        for m in re.finditer(r'cada\s+questão\s+da\s+prova\s+objetiva\s+valerá\s+(\d+(?:[,.]\d+)?)',texto,re.I):
            pesos.append({'Peso':float(m[1].replace(',','.')),'Página':i,'Trecho':texto[m.start():m.end()+100]})
    return candidatos,datas,questoes,pesos
