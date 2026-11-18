from collections import defaultdict

def grupos(questoes,pesos):
    por_pagina=defaultdict(list)
    for q in questoes:
        if q not in por_pagina[q['Página']]: por_pagina[q['Página']].append(q)
    return dict(por_pagina)

def ranking(rows,peso):
    if not rows or peso<=0: return []
    total=sum(r['Questões']*peso for r in rows)
    return sorted([dict(r,**{'Pontos':round(r['Questões']*peso,4),'Participação (%)':round(100*r['Questões']*peso/total,2)}) for r in rows],key=lambda r:-r['Pontos'])
