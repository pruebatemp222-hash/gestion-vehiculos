import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuración de la página ---
st.set_page_config(page_title="Gestión de Vehículos", layout="centered", page_icon="🚗")
st.title("Gestión de Vehículos 🚗")

# --- 2. Conexión a Google Sheets ---
# Usamos cache para no reconectarnos en cada clic y hacer la app más rápida
@st.cache_resource
def conectar_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Busca el archivo de llave secreta que descargaremos de Google
    credenciales = Credentials.from_service_account_file("credenciales.json", scopes=scopes)
    cliente = gspread.authorize(credenciales)
    
    # Conecta con tu archivo de Google Sheets
    hoja = cliente.open("Vehiculos_App").sheet1
    return hoja

try:
    hoja_datos = conectar_sheets()
except FileNotFoundError:
    st.error("⚠️ Falta el archivo 'credenciales.json'. Necesitamos conectarlo a Google Cloud.")
    st.stop()
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")
    st.stop()

# --- 3. Formulario para agregar vehículos ---
st.subheader("Agregar Nuevo Vehículo")

# Usamos st.form para agrupar los datos antes de enviarlos
with st.form("form_vehiculo", clear_on_submit=True):
    placa = st.text_input("Placa del Vehículo:")
    propietario = st.text_input("Nombre del Propietario:")
    
    # Botón principal del formulario
    enviado = st.form_submit_button("Agregar Vehículo")

    if enviado:
        if placa and propietario:
            # Traemos los datos actuales para calcular el siguiente "N°"
            datos_actuales = hoja_datos.get_all_records()
            nuevo_numero = len(datos_actuales) + 1
            
            # Insertar la nueva fila directamente en Google Sheets
            hoja_datos.append_row([nuevo_numero, placa, propietario])
            st.success(f"Vehículo {placa} agregado correctamente a la nube.")
        else:
            st.warning("Por favor, completa ambos campos.")

# --- 4. Mostrar la tabla de registros ---
st.subheader("Registros Actuales")

# Traer la información fresca y mostrarla
datos = hoja_datos.get_all_records()

if datos:
    df = pd.DataFrame(datos)
    # Mostramos los datos en una tabla web interactiva
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No hay vehículos registrados aún.")