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
    # 1. Validar que los secretos de GCP existan en Streamlit
    if "gcp_service_account" not in st.secrets:
        st.error("⚠️ No se encontraron las credenciales en st.secrets.")
        st.stop()
        
    # 2. Obtener el diccionario de secretos
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # 3. CORRECCIÓN CRÍTICA (Error PEM): 
    # Asegurar que los saltos de línea literales se conviertan en saltos reales
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    # 4. Crear credenciales a partir del diccionario limpio
    creds = Credentials.from_service_account_info(creds_dict)
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    scoped_creds = creds.with_scopes(scopes)
    cliente = gspread.authorize(scoped_creds)
    
    # 5. Conecta con tu archivo de Google Sheets (asegúrate de que se llame exactamente así)
    hoja = cliente.open("Vehiculos_App").sheet1
    return hoja

# Intentar la conexión y manejar posibles errores visualmente
try:
    hoja_datos = conectar_sheets()
except Exception as e:
    st.error(f"❌ Error al conectar con Google Sheets: {e}")
    st.info("💡 Revisa que hayas configurado tus Secrets correctamente y que hayas compartido el Google Sheet con el correo 'client_email' de tu JSON.")
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
            st.success(f"✅ Vehículo {placa} agregado correctamente a la base de datos.")
        else:
            st.warning("⚠️ Por favor, completa ambos campos antes de enviar.")

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
