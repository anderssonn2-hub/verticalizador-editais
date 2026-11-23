import streamlit as st
from universal import paginas, localizar, extrair, cargos
from extrator_raiox import analisar
from identificador import identificar, chave
from consolidar import consolidar, calendario
from pontuacao import grupos, ranking
from datetime import date, datetime
from estrutura import opcoes, campos_extra
from cronograma import tabela_datas
import hashlib

def mostrar_raio_x():
    st.subheader('Raio-X do edital')
    st.caption('V3.0.11 DEV · Resumo automático do edital. Consulte as fontes se precisar.')
    pdf=st.file_uploader('Edital do concurso',type=['pdf'],key='raiox_pdf')
    if pdf is None: return
    doc=hashlib.sha256(pdf.getvalue()).hexdigest()[:16]
    try:
        from leitura_pdf import ler
        if 'leitura_'+doc not in st.session_state:
            barra=st.progress(0,text='Lendo edital e reconhecendo imagens quando necessário…')
            try: st.session_state['leitura_'+doc]=ler(pdf.getvalue(),lambda i,n:barra.progress(i/n,text=f'Lendo página {i} de {n}'))
            finally: barra.empty()
        pgs,ocr=st.session_state['leitura_'+doc]
        if ocr: st.caption(f'OCR automático: {len(ocr)} páginas. A leitura pode conter erros de reconhecimento.')
    except Exception as e: st.error(f'Não foi possível ler o PDF: {e}'); return
    if not any(p.strip() for p in pgs): st.warning('PDF sem texto pesquisável. OCR ainda não disponível.'); return
    start,end=localizar(pgs)
    nomes,campos=identificar(pgs)
    for nome in cargos(pgs):
        if chave(nome) not in {chave(x['Cargo']) for x in nomes}: nomes.append({'Cargo':nome,'Página':None,'Trecho':'Cabeçalho detectado'})
    nomes,campos=consolidar(nomes,campos)
    from conteudo import parse, selected
    blocks, detected = parse(pgs)
    opts=detected or opcoes(pgs)
    if blocks:
        source_pages=[p for b in blocks for p,_ in b['parts']]
        if source_pages: start,end=min(source_pages),max(source_pages)
    if opts: nomes=[dict(Cargo=x,Página=start,Trecho="Cabeçalho do conteúdo programático") for x in opts]

    # V3.0.11 - Eliminar cargos duplicados por grafia
    cargos_unicos = {}
    for item in nomes:
        nome = item['Cargo'].strip()
        identificador = chave(nome)
        if identificador not in cargos_unicos:
            cargos_unicos[identificador] = item

    nomes = list(cargos_unicos.values())

    campos+=campos_extra(pgs)
    candidatos,datas,questoes,pesos=analisar(pgs)
    a,b,c=st.columns(3); a.metric('Páginas',len(pgs)); b.metric('Possíveis cargos',len(nomes)); c.metric('Conteúdo sugerido',f'{start}–{end}')
    st.subheader('Identificação do concurso')
    doc=hashlib.sha256(pdf.getvalue()).hexdigest()[:16]
        # V3.0.11 - Garantir cargos únicos antes dos cartões
    nomes_filtrados = []
    chaves_vistas = set()

    for item in nomes:
        nome = item['Cargo'].strip()
        codigo_nome = chave(nome)

        if codigo_nome in chaves_vistas:
            continue

        chaves_vistas.add(codigo_nome)
        nomes_filtrados.append(item)

    nomes = nomes_filtrados
    lista = [item['Cargo'] for item in nomes]
    st.write("DIAGNÓSTICO V3.0.11 — ARQUIVO ATUALIZADO")
    st.write("Cargos recebidos:", repr(lista))
    st.write("Total de cargos:", len(lista))
    st.write("Chaves normalizadas:", [chave(n) for n in lista])
    escolha=None
    from cargo_dados import extrair_dados, prova_por_cargo, complementar_dados_cargo_unico
    dados=extrair_dados(pgs,lista)
    dados=complementar_dados_cargo_unico(pgs,dados)

    # V3.0.11 - Vagas extraidas de tabelas do PDF
    import re
    from vagas_tabelas import extrair_vagas_tabelas

    # V3.0.11 - Cache das vagas por documento
    chave_vagas = "vagas_tabelas_" + doc

    if chave_vagas not in st.session_state:
        st.session_state[chave_vagas] = extrair_vagas_tabelas(
            pdf.getvalue()
        )

    vagas_por_codigo = st.session_state[chave_vagas]

    for nome_cargo in lista:
        codigo_encontrado = re.match(
            r"^\s*(\d{1,4})\s*[-–—.:)]",
            nome_cargo
        )

        if not codigo_encontrado:
            continue

        codigo_cargo = codigo_encontrado.group(1)
        registro = vagas_por_codigo.get(codigo_cargo)

        if registro and dados[nome_cargo].get("vagas") is None:
            dados[nome_cargo]["vagas"] = registro["vagas"]
            dados[nome_cargo]["paginas"].add(registro["pagina"])
    for campo in ['Órgão','Banca']:
        valores=list(dict.fromkeys(x['Valor'] for x in campos if x['Campo']==campo))
        st.text(f'{campo}: '+ (' · '.join(valores) if valores else 'Não localizado'))
    if lista:
        key='cargo_card_'+doc
        if st.session_state.get(key) not in lista: st.session_state[key]=lista[0] if len(lista)==1 else None
        st.markdown('### Cargos disponíveis')
        for inicio in range(0,len(lista),2):
            cols=st.columns(2)
            for j,nome in enumerate(lista[inicio:inicio+2]):
                d=dados[nome]
                with cols[j], st.container(border=True):
                    st.markdown('**'+nome+'**')
                    st.caption('Remuneração mensal')
                    st.markdown('### '+(d['salario'] or 'Não localizada'))
                    st.write('Vagas: '+('Cadastro de reserva' if d['vagas']=='CR' else d['vagas'] or 'Não localizadas'))
                    if d['taxa']: st.caption('Taxa de inscrição: '+d['taxa'])
                    if d.get('jornada'): st.caption('Jornada de trabalho: '+d['jornada'])
                    if d['paginas']: st.caption('PDF · p. '+', '.join(map(str,sorted(d['paginas']))))
                    if st.button('Selecionado' if st.session_state[key]==nome else 'Selecionar cargo',key=f'{key}_{inicio+j}',type='primary' if st.session_state[key]==nome else 'secondary',use_container_width=True):
                        st.session_state[key]=nome; st.rerun()
        escolha=st.session_state[key]
        if escolha: st.success('Cargo selecionado: '+escolha)
        else: st.caption('Selecione um cargo para visualizar seu conteúdo.')
    with st.expander('Fontes da identificação'): st.dataframe(campos,hide_index=True); st.dataframe(nomes,hide_index=True)
    st.subheader('Cronograma do concurso')
    prova = None
    relevantes=tabela_datas(pgs)
    fallback=calendario(pgs)
    existentes={r['Evento'] for r in relevantes}
    relevantes += [r for r in fallback if r['Evento'] not in existentes]
    doc=hashlib.sha256(pdf.getvalue()).hexdigest()[:16]
    for evento in ['Início das inscrições','Encerramento das inscrições','Data prevista da prova']:
        vals=[r for r in relevantes if r['Evento']==evento]
        if evento=='Data prevista da prova':
            op=list(dict.fromkeys(r['Data'] for r in vals))
            auto=datetime.strptime(op[0],'%d/%m/%Y').date() if len(op)==1 else None
            prova=st.session_state.get('data_final_'+doc,auto)
            st.markdown(f"**{evento}:** "+(prova.strftime('%d/%m/%Y') if prova else 'Datas divergentes' if op else 'Não localizada'))
            if len(op)>1: st.caption('Datas encontradas: '+ ' · '.join(op))
            if prova!=auto: st.caption('Data ajustada manualmente.')
            with st.expander('Editar data da prova'):
                nova=st.date_input('Data corrigida',value=prova,format='DD/MM/YYYY',min_value=date(1900,1,1),max_value=date(2100,12,31),key='edicao_'+doc)
                if st.button('Salvar ajuste',key='salvar_'+doc):
                    st.session_state['data_final_'+doc]=nova
                    st.rerun()
        else:
            st.markdown(f"**{evento}:** "+ (' · '.join(r['Data'] for r in vals) if vals else 'Não localizado'))
            if len(vals)>1: st.caption('Datas alternativas — conferir retificações.')
    with st.expander('Fontes do cronograma'): st.dataframe(relevantes,hide_index=True)
    if prova:
        dias=(prova-date.today()).days
        if dias>=0: st.metric('Dias até a prova',dias)
        else: st.info(f'A data da prova passou há {-dias} dias.')
    st.subheader('Estrutura da prova')
    prova_dados=prova_por_cargo(pgs,dados[escolha]['codigo']) if escolha else None
    if prova_dados:
        st.metric('Questões objetivas',prova_dados['total'])
        if prova_dados['rows']:
            rows=prova_dados['rows']; total=sum(r['Questões']*r['Peso'] for r in rows)
            for r in rows: r['Pontos']=r['Questões']*r['Peso']; r['Participação (%)']=round(100*r['Pontos']/total,2)
            st.dataframe(rows,hide_index=True); st.bar_chart(rows,x='Grupo',y='Pontos')
        else: st.info('Distribuição ou pesos não confirmados pela leitura. Consulte a fonte.')
        with st.expander('Fonte da estrutura da prova'): st.caption(f"PDF · página {prova_dados['pagina']}"); st.text(prova_dados['texto'])
    else: st.info('Selecione um cargo ou consulte o edital: estrutura por cargo não localizada com segurança.')
    st.subheader('Conteúdo programático')
    from estrutura import itens
    if blocks and escolha:
        fontes=set(); cards=selected(blocks,escolha)
        for grupo in ['Conhecimentos gerais','Conhecimentos específicos','Classificação não identificada']:
            subset=[r for r in cards if r['Grupo']==grupo]
            if not subset and grupo.startswith('Classificação'): continue
            st.markdown('### '+grupo)
            if not subset: st.warning('Não foi possível associar conteúdo a este grupo com segurança.'); continue
            st.caption(f'{len(subset)} blocos de disciplinas')
            for r in subset:
                fontes.update(int(x) for x in r['Páginas'].split(', '))
                with st.expander(f"{r['Disciplina']} · PDF p. {r['Páginas']}"):
                    for t in r['Assuntos']: st.write(t)
        st.caption('Segmentação por padrões; confira a íntegra e possíveis erros de OCR. Não representa uma hierarquia oficial de subtópicos.')
    elif opts and escolha in opts:
        rows=itens(pgs,escolha,detalhes=True)
        fontes=set()
        for grupo in ['Conhecimentos gerais','Conhecimentos específicos']:
            subset=[r for r in rows if r['Grupo']==grupo]
            st.markdown('### '+grupo)
            if subset:
                st.dataframe([{k:v for k,v in r.items() if k!='Grupo'} for r in subset],hide_index=True)
                for r in subset: fontes.update(int(x) for x in r['Páginas'].split(', ') if x)
            else: st.info('Conteúdo não localizado para este grupo.')
    elif opts:
        fontes=set(); st.info('Selecione um cargo acima.')
    else:
        fontes=set() if (start,end)==(1,len(pgs)) else set(range(start,end+1))
        st.caption('Classificação entre conhecimentos gerais e específicos ainda não validada para este formato.')
        rows=extrair(pgs,start,end,cargo=escolha) if fontes else []
        if rows: st.dataframe(rows,hide_index=True)
        else: st.info('Nenhum assunto localizado.')
    if fontes:
        st.caption('Páginas de origem no PDF: '+', '.join(map(str,sorted(fontes))))
        with st.expander('Conferir texto original'):
            for page in sorted(fontes):
                st.markdown(f'**Página {page} do PDF**')
                st.text(pgs[page-1])
    st.caption('A associação universal por cargo e a leitura de tabelas continuam em desenvolvimento.')
