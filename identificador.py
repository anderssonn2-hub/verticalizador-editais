import re
import unicodedata

def chave(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.casefold()) if not unicodedata.combining(c))

def identificar(pgs):
    cargos={}; campos=[]
    for i,p in enumerate(pgs,1):
        t=' '.join(p.split())
        for m in re.finditer(r'\b(?:para o cargo de|cargo de|cargo\s*:)\s*([^,;:.]{3,100})',t,re.I):
            nome=re.split(r'\s+(?:a que|ao qual|da carreira|será|é|deverá|se |previsto|para |com |nos termos|e será|do quadro|que |pertencente|destinado|no presente)\b',m[1],maxsplit=1,flags=re.I)[0].strip(' -')
            if len(nome.split())>9 or len(nome)<3 or re.search(r'\d|\b(?:provimento|concurso|candidato|referido|público)\b',nome,re.I): continue
            k=chave(nome); cargos.setdefault(k,{'Cargo':nome,'Página':i,'Trecho':m.group()})
        if i<=2:
            for m in re.finditer(r'^\s*CARGO DE (.{3,80})$',p,re.I|re.M):
                nome=m[1].strip().title(); cargos.setdefault(chave(nome),{'Cargo':nome,'Página':i,'Trecho':m.group()})
            for m in re.finditer(r'TRIBUNAL REGIONAL FEDERAL DA\s+(\d{1,2})(?:[. ]?2|[ªºa])?\s+REGIÃO',p,re.I):
                numero=m[1]; numero=numero[0] if len(numero)==2 and numero.endswith('2') else numero
                campos.append({'Campo':'Órgão','Valor':f'Tribunal Regional Federal da {numero}ª Região','Página':i,'Trecho':m.group()})
        if i<=15:
            for campo,pat in [('Vagas',r'\b(\d[\d.]*)\s*(?:\([^)]{1,80}\)\s*)?vagas\b'),('Remuneração',r'(?:remuneração(?: inicial)?|vencimento(?:s)?|subsídio|salário)[^.;]{0,100}?(R\$\s*[\d.]+,\d{2})'),('Banca',r'(Fundação\s+Get[uú]lio\s+Vargas|CEBRASPE|CESPE|Fundação Carlos Chagas|VUNESP|Instituto AOCP|IBFC|Instituto ACCESS|Instituto Quadrix|FUNDATEC|Consulplan)'),('Órgão',r'(Polícia Civil (?:do Estado )?de [A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+)?)')]:
                for m in re.finditer(pat,t,re.I if campo!='Órgão' else 0):
                    campos.append({'Campo':campo,'Valor':m[1],'Página':i,'Trecho':t[max(0,m.start()-65):m.end()+65]})
    return list(cargos.values()),campos
