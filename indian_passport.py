import streamlit as st
from PIL import Image
import pytesseract
import re
from passporteye import read_mrz
import pycountry

# Configure path to tesseract executable
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Streamlit Page Setup
st.set_page_config(page_title="🛂 EU Passport Extractor", layout="centered")
st.title("🛂 EU Passport Information Extractor")

# File Upload
uploaded_file = st.file_uploader("📷 Upload an image of the passport", type=["jpg", "jpeg", "png"])

# -------------------------------
# Function: Expand country codes
# -------------------------------
def get_country_fullname(code):
    try:
        country = pycountry.countries.get(alpha_3=code.upper())
        return f"{country.name} ({code.upper()})"
    except:
        return code

# -------------------------------
# Function: Extract info using Tesseract OCR
# -------------------------------
def extract_text_info(image):
    text = pytesseract.image_to_string(image)
    info = {}

    # Regex for matching various fields (Optional — depends on formatting)
    name_match = re.search(r'P<\w+<<([A-Z<]+)', text)
    passport_number = re.search(r'\b([A-Z0-9]{8,9})\b', text)

    if name_match:
        info["Name"] = name_match.group(1).replace("<", " ").strip().title()
    if passport_number:
        info["Passport Number"] = passport_number.group(1)

    return info, text

# -------------------------------
# Function: Extract MRZ data
# -------------------------------
def extract_mrz_info(image):
    mrz = read_mrz(image)
    if mrz:
        raw = mrz.to_dict()
        # Fixing name extraction from MRZ
        surname = raw.get("surname", "").replace("<", " ").strip().title()
        names = raw.get("names", "").replace("<", " ").strip().title()
        
        # Correcting name extraction (first name is in the second part of names)
        first_name = names.replace(surname, "").strip()

        info = {
            "Raw MRZ": raw.get("mrz_text", ""),
            "Country Code (Issued By)": get_country_fullname(raw.get("country", "")),
            "Passport Number": raw.get("number", "").replace("<", ""),
            "Last Name": surname,
            "First Name": first_name,
            "Nationality": get_country_fullname(raw.get("nationality", "")),
            "Date of Birth": convert_date(raw.get("date_of_birth", "")),
            "Expiration Date": convert_date(raw.get("expiration_date", "")),
            "Sex": raw.get("sex", ""),
        }
        return info
    return {}

# -------------------------------
# Helper: Convert date from YYMMDD to DD/MM/YYYY
# -------------------------------
def convert_date(ymd):
    if len(ymd) != 6:
        return ymd
    yy = int(ymd[:2])
    mm = ymd[2:4]
    dd = ymd[4:]
    year = 1900 + yy if yy > 30 else 2000 + yy
    return f"{dd}/{mm}/{year}"

# -------------------------------
# Streamlit Logic
# -------------------------------
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="📄 Uploaded Passport", use_column_width=True)

    with st.spinner("🔍 Extracting info..."):
        extracted_info, raw_text = extract_text_info(image)
        mrz_info = extract_mrz_info(uploaded_file)

    # Show raw OCR text
    st.subheader("📜 OCR Text:")
    st.text_area("Raw OCR Text", raw_text, height=200)

    # Show extracted basic info
    st.subheader("📌 Extracted Info (from text):")
    if extracted_info:
        for key, value in extracted_info.items():
            st.write(f"**{key}:** {value}")
    else:
        st.warning("⚠️ OCR couldn’t extract reliable info. Try clearer photo or rely on MRZ.")

    # Show MRZ Info
    if mrz_info:
        st.subheader("🔎 MRZ Extracted Info:")
        for key, value in mrz_info.items():
            st.write(f"**{key}:** {value}")
    else:
        st.error("❌ No valid MRZ data found.")

    # Download OCR text
    st.download_button("⬇️ Download OCR Text", data=raw_text, file_name="passport_text.txt")
