import pdfplumber

def extraire_texte(chemin_pdf):   # ← chemin_pdf arrive depuis app.py
    texte = ""
    with pdfplumber.open(chemin_pdf) as pdf:
        for page in pdf.pages:
            texte += page.extract_text() + "\n"
    return texte
# -------- TEST --------
if __name__ == "__main__":
    chemin = r"C:\Users\wafae\Desktop\srm-intelligent-billing-system\data\facture_electricite_client1.pdf"
    texte = extraire_texte(chemin)
    print(texte)