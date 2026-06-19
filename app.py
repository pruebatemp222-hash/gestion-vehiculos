import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuración de la página ---
st.set_page_config(page_title="Gestión de Vehículos", layout="centered", page_icon="🚗")
st.title("Gestión de Vehículos 🚗")

# --- 2. Conexión a Google Sheets ---
@st.cache_resource
def conectar_sheets():
    # 1. Validar que el secreto exista
    if "gcp_service_account" not in st.secrets:
        st.error("⚠️ No se encontraron las credenciales en st.secrets.")
        st.stop()
        
    # 2. Obtener el diccionario de secretos
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # 3. CORRECCIÓN CRÍTICA: Asegurar que los saltos de línea de la llave privada sean válidos
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # Crear credenciales
    creds = Credentials.from_service_account_info(creds_dict)
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    scoped_creds = creds.with_scopes(scopes)
    cliente = gspread.authorize(scoped_creds)
    
    # Conectar con el archivo de Google Sheets
    # Asegúrate de que el nombre coincida EXACTAMENTE con tu archivo en Drive
    hoja = cliente.open("Vehiculos_App").sheet1
    return hoja

# Intentar la conexión
try:
    hoja_datos = conectar_sheets()
except Exception as e:
    st.error(f"❌ Error de conexión con Google Sheets: {e}")
    st.info("Revisa que hayas configurado correctamente tus Secrets en Streamlit y que hayas compartido el Google Sheet con el 'client_email' de tu JSON.")
    st.stop()

# --- El resto de tu código (Formulario y Tabla) queda igual ---
