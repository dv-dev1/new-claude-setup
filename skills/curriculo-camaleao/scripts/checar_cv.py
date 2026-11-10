"""Verificador objetivo do Currículo Camaleão.

Uso:
  python3 checar_cv.py <vaga-keywords.txt>           -> só o fit da vaga (triagem)
  python3 checar_cv.py <vaga-keywords.txt> <cv.pdf>  -> fit + validação do PDF

Arquivo de keywords: um termo por linha, escrito como a vaga escreve.
  *Termo   obrigatório da vaga
  Termo    desejável
  !Termo   gap real (não existe em candidato.md); combine: *!Termo
  A|B      requisito "A ou B": basta um aparecer no PDF
  # linha de comentário
Termos proibidos vêm de ../references/proibidos.txt (mesmo formato, sem prefixos).
Sai com código 1 se o PDF reprovar.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROIBIDOS = Path(__file__).resolve().parent.parent / "references" / "proibidos.txt"


def ler_termos(conteudo):
    termos = []
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        prefixo = re.match(r"[*!]*", linha).group(0)
        termos.append((linha[len(prefixo):].strip(), "*" in prefixo, "!" in prefixo))
    return termos


def achar(termo, texto):
    # Casamento literal, como um ATS: sem sinônimo, sem plural, com fronteira de palavra.
    # "A|B" é requisito "A ou B": basta um.
    alvo = " ".join(texto.split()).casefold()
    for alt in termo.split("|"):
        t = " ".join(alt.split()).casefold()
        if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", alvo):
            return True
    return False


def quebras_hifen(texto):
    return re.findall(r"[^\W\d_]+-(?=[ \t]*$)", texto, re.M)


def rodar(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def main(argv):
    if len(argv) not in (2, 3):
        sys.exit("uso: python3 checar_cv.py <vaga-keywords.txt> [cv.pdf]")
    termos = ler_termos(Path(argv[1]).read_text(encoding="utf-8"))

    obrig = [t for t in termos if t[1]]
    gaps_obrig = [t[0] for t in obrig if t[2]]
    if obrig:
        ok = len(obrig) - len(gaps_obrig)
        linha = f"Fit nos obrigatórios: {ok}/{len(obrig)} ({100 * ok // len(obrig)}%)"
        print(linha + (f" | gaps reais: {', '.join(gaps_obrig)}" if gaps_obrig else ""))
    else:
        print("Fit nos obrigatórios: vaga sem obrigatórios marcados com *")
    gaps_desej = [t[0] for t in termos if not t[1] and t[2]]
    if gaps_desej:
        print(f"Gaps reais nos desejáveis: {', '.join(gaps_desej)}")
    if len(argv) == 2:
        return 0

    if not shutil.which("pdftotext"):
        sys.exit("pdftotext não encontrado: brew install poppler (Mac) ou dnf install poppler-utils (Fedora)")
    pdf = argv[2]
    texto = rodar("pdftotext", pdf, "-")
    paginas = int(re.search(r"Pages:\s+(\d+)", rodar("pdfinfo", pdf)).group(1))

    falhas = []
    if paginas != 1:
        falhas.append(f"{paginas} páginas; o limite é 1")
    cortes = quebras_hifen(rodar("pdftotext", "-layout", pdf, "-"))
    if cortes:
        falhas.append(f"palavras cortadas por hífen no fim da linha: {', '.join(cortes)}")
    comprovados = [t for t in termos if not t[2]]
    faltando = [t[0] for t in comprovados if not achar(t[0], texto)]
    if faltando:
        falhas.append(f"keywords comprovadas ausentes do PDF: {', '.join(faltando)}")
    proibidos = [t[0] for t in ler_termos(PROIBIDOS.read_text(encoding="utf-8")) if achar(t[0], texto)]
    if proibidos:
        falhas.append(f"termos proibidos no PDF: {', '.join(proibidos)}")

    print(f"Páginas: {paginas}")
    print(f"Cobertura no PDF: {len(comprovados) - len(faltando)}/{len(comprovados)} keywords comprovadas")
    gaps_no_pdf = [t[0] for t in termos if t[2] and achar(t[0], texto)]
    if gaps_no_pdf:
        print(f"Atenção, gap real aparece no PDF (só como 'em estudo'): {', '.join(gaps_no_pdf)}")
    if falhas:
        print("REPROVADO")
        for f in falhas:
            print(f"- {f}")
        return 1
    print("APROVADO")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
