import os, re, shutil, subprocess, tempfile
from pathlib import Path
import fitz

def limpar(texto):
    return '\n'.join(l for l in texto.splitlines() if not re.match(r'\s*(pcimarkpci|www\.pciconcursos\.com\.br)',l,re.I))

def executavel():
    candidatos=[os.environ.get('TESSERACT_CMD'),shutil.which('tesseract'),r'C:\Program Files\Tesseract-OCR\tesseract.exe']
    return next((x for x in candidatos if x and Path(x).is_file()),None)

def ler(pdf, progresso=None):
    textos=[]; ocr=[]; exe=None
    with fitz.open(stream=pdf,filetype='pdf') as doc, tempfile.TemporaryDirectory() as tmp:
        for i,p in enumerate(doc):
            t=limpar(p.get_text(sort=True))
            if len(re.findall(r'\b[^\W\d_]{3,}\b',t))<35 and (p.get_images() or len(t.strip())<80):
                if not exe:
                    exe=executavel()
                    if not exe: raise RuntimeError('PDF exige OCR. Instale Tesseract OCR com idioma português (por).')
                f=str(Path(tmp)/'pagina.png'); p.get_pixmap(dpi=300,alpha=False).save(f)
                r=subprocess.run([exe,f,'stdout','-l','por','--psm','3'],capture_output=True,timeout=180,env={**os.environ,'OMP_THREAD_LIMIT':'2'})
                if r.returncode: raise RuntimeError(r.stderr.decode('utf-8',errors='replace'))
                t=limpar(r.stdout.decode('utf-8',errors='replace')); ocr.append(i+1)
            textos.append(t)
            if progresso: progresso(i+1,len(doc))
    return textos,ocr
