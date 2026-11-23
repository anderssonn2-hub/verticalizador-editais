
import re
import unicodedata

def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", texto).strip().casefold()

def interpretar_vagas(valor):
    texto = normalizar(valor)
    texto = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰*]+$", "", texto).strip()

    if re.search(r"cadastro\s*de\s*reserva", texto):
        return "CR"

    if re.fullmatch(r"c\.?\s*r\.?", texto):
        return "CR"

    if re.fullmatch(r"\d[\d.]*", texto):
        return texto

    return None

def extrair_vagas_tabelas(pdf_bytes):
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf

    resultado = {}

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for pagina_numero, pagina in enumerate(doc, 1):
            tabelas = pagina.find_tables()

            for tabela in tabelas.tables:
                linhas = tabela.extract()

                for linha in linhas:
                    if not linha or len(linha) < 3:
                        continue

                    codigo = str(linha[0] or "").strip()

                    if not re.fullmatch(r"\d{1,4}", codigo):
                        continue

                    nome = str(linha[1] or "").strip()

                    if not nome:
                        continue

                    # Somente o campo imediatamente posterior ao nome.
                    # Nunca utilizar valores de colunas de cotas.
                    vagas = interpretar_vagas(linha[2])

                    if vagas is None:
                        continue

                    if codigo not in resultado:
                        resultado[codigo] = {
                            "vagas": vagas,
                            "pagina": pagina_numero,
                            "cargo_tabela": nome
                        }

    return resultado
