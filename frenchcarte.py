import streamlit as st
from PIL import Image
import pytesseract
import re
from passporteye import read_mrz
import pycountry
from datetime import datetime

# Configure path to Tesseract executable (adjust as needed)


# --- Streamlit Page Setup ---
st.set_page_config(page_title="Extracteur Carte Nationale d'Identité Française", layout="centered")
st.title("Extracteur d'Informations de la Carte Nationale d'Identité Française")

# File upload
uploaded_file = st.file_uploader("📷 Téléchargez une image de la pièce d'identité", type=["jpg", "jpeg", "png"])

# -------------------------------
# Helper: Expand country codes to full names
# -------------------------------
def get_country_fullname(code):
    try:
        country = pycountry.countries.get(alpha_3=code.upper())
        return f"{country.name} ({code.upper()})"
    except Exception:
        return code

# -------------------------------
# Helper: Convert date (can be from MRZ or OCR) to DD/MM/YYYY
# Accepts formats like YYMMDD (MRZ) or dd.mm.yyyy / dd/mm/yyyy
# -------------------------------
def convert_date(date_str):
    date_str = date_str.strip()
    # If format is YYMMDD (MRZ)
    if re.fullmatch(r'\d{6}', date_str):
        yy = int(date_str[:2])
        mm = date_str[2:4]
        dd = date_str[4:]
        year = 1900 + yy if yy > 30 else 2000 + yy
        return f"{dd}/{mm}/{year}"
    # If format is dd.mm.yyyy or dd/mm/yyyy
    m = re.fullmatch(r'(\d{2})[./-](\d{2})[./-](\d{4})', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return date_str  # fallback

# -------------------------------
# Helper: Extract "taille" (size/height) from OCR text
# -------------------------------
def extract_taille(ocr_text):
    match = re.search(r'(?:Taille|T\.|taille)[\s:]*([\d.,]+)', ocr_text)
    if match:
        return match.group(1).replace(',', '.').strip()
    return "Non précisé"

# -------------------------------
# Function: Extract additional info from OCR text via regex (fallback extraction)
# -------------------------------
def extract_info_from_ocr_text(ocr_text):
    info = {}
    # Extraction for Carte Nationale d'Identité (ID number)
    id_match = re.search(r"CARTE NATIONALE D'?IDENTITE(?:\s*Ne\s*[:]?[\s]*)(\d+)", ocr_text, re.IGNORECASE)
    if id_match:
        info["Carte nationale d'identité"] = id_match.group(1)
    # Nationalité extraction
    nat_match = re.search(r"Nationalité\s*[:]?[\s]*([A-Za-zéèàùçÉÈÀÙÇ]+)", ocr_text, re.IGNORECASE)
    if nat_match:
        info["Nationalité"] = nat_match.group(1).title()
    # Nom de famille extraction (look for "Nom:" or "BC Nom:")
    nom_match = re.search(r"(?:BC\s*)?Nom\s*[:]?[\s]*([A-Z]+)", ocr_text, re.IGNORECASE)
    if nom_match:
        info["Nom de famille"] = nom_match.group(1).title()
    # Prénom(s) extraction
    prenom_match = re.search(r"Prénom[\(\{]?[sS]?[}\)]?\s*[:]?[\s]*([A-Z]+)", ocr_text, re.IGNORECASE)
    if prenom_match:
        info["Prénom"] = prenom_match.group(1).title()
    # Sexe extraction
    sexe_match = re.search(r"Sexe\s*[:]?[\s]*([FM])", ocr_text, re.IGNORECASE)
    if sexe_match:
        info["Sexe"] = sexe_match.group(1).upper()
    # Date of Birth extraction - updated regex to capture variations (e.g. Né(e) le or Né(e} ie:)
    dob_match = re.search(r"N[éeÉÈ]*[\(\{]?e[\)\}]?\s*(?:le|ie)?\s*[:]?\s*([\d]{2}[./-][\d]{2}[./-][\d]{4})", ocr_text, re.IGNORECASE)
    if dob_match:
        info["Né(e) le"] = convert_date(dob_match.group(1))
    # Taille extraction
    info["Taille"] = extract_taille(ocr_text)
    return info

# -------------------------------
# Function: Extract MRZ info and map to French fields
# -------------------------------
def extract_mrz_info(image):
    mrz = read_mrz(image)
    if mrz:
        raw = mrz.to_dict()
        # Extract surname and names, clean out '<'
        surname = raw.get("surname", "").replace("<", " ").strip().title()
        names = raw.get("names", "").replace("<", " ").strip().title()
        # Determine first name (Prénom)
        if names:
            if surname and surname in names:
                prenom = names.replace(surname, "").strip()
                if prenom == "":
                    prenom = names
            else:
                prenom = names
        else:
            prenom = "Non précisé"

        dob_raw = raw.get("date_of_birth", "").replace("<", "").strip()
        exp_raw = raw.get("expiration_date", "").replace("<", "").strip()
        sexe = raw.get("sex", "").replace("<", "").strip() or "Non précisé"

        info = {
            "MRZ brut": raw.get("mrz_text", ""),
            "Pays de délivrance": get_country_fullname(raw.get("country", "")),
            "Carte nationale d'identité": raw.get("number", "").replace("<", ""),
            "Nom de famille": surname,
            "Prénom": prenom,
            "Nationalité": get_country_fullname(raw.get("nationality", "")),
            "Né(e) le": convert_date(dob_raw),
            "Date d'expiration": convert_date(exp_raw),
            "Sexe": sexe,
        }
        return info
    return {}

# -------------------------------
# Streamlit App Logic
# -------------------------------
selected_languages = st.selectbox("Sélectionnez la langue OCR", ["eng", "fra", "eng+fra", "eng+fra+deu"])
    
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image téléchargée", use_column_width=True)

    with st.spinner("Extraction des informations..."):
        ocr_text = pytesseract.image_to_string(image, lang=selected_languages)
        mrz_info = extract_mrz_info(uploaded_file)
        ocr_info = extract_info_from_ocr_text(ocr_text)
        taille = extract_taille(ocr_text)

    st.subheader("Texte OCR brut :")
    st.text_area("OCR", ocr_text, height=200)

    st.subheader("Informations extraites :")
    final_info = {}
    if mrz_info:
        final_info.update(mrz_info)
    final_info.update(ocr_info)
    final_info["Taille"] = taille

    if final_info:
        for field, value in final_info.items():
            st.write(f"**{field} :** {value}")
    else:
        st.error("Aucune information n'a pu être extraite.")

    st.download_button("⬇️ Télécharger le texte OCR", data=ocr_text, file_name="texte_identite.txt")
