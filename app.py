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
    creds_dict = dict(st.secrets["gcp_service_account"])
    # Limpiamos la clave privada por seguridad (tu corrección anterior)
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    cliente = gspread.authorize(creds.with_scopes(scopes))
    return cliente.open("Vehiculos_App").sheet1

try:
    hoja_datos = conectar_sheets()
except Exception as e:
    st.error(f"❌ Error al conectar con Google Sheets: {e}")
    st.stop()

# Traemos la información fresca al inicio para usarla en toda la app
datos = hoja_datos.get_all_records()
df = pd.DataFrame(datos) if datos else pd.DataFrame()

# --- 3. Formulario para agregar vehículos ---
st.subheader("1. Agregar Nuevo Vehículo")
with st.form("form_vehiculo", clear_on_submit=True):
    placa = st.text_input("Placa del Vehículo:")
    propietario = st.text_input("Nombre del Propietario:")
    enviado = st.form_submit_button("Agregar Vehículo")

    if enviado:
        if placa and propietario:
            nuevo_numero = len(datos) + 1 if datos else 1
            # Insertamos la fila con espacios vacíos para las horas que se llenarán después
            hoja_datos.append_row([nuevo_numero, placa, propietario, "", ""])
            st.success(f"✅ Vehículo {placa} agregado correctamente a la nube.")
            st.rerun() # Recarga la página automáticamente para ver el cambio
        else:
            st.warning("⚠️ Por favor, completa ambos campos.")

# --- 4. NUEVO: Registrar Ingreso / Salida ---
st.subheader("2. Marcar Hora de Ingreso / Salida")
if not df.empty:
    with st.form("form_tiempos"):
        # Convertimos las placas a texto para evitar errores y las mostramos en una lista
        lista_placas = df["Placa"].astype(str).tolist()
        placa_seleccionada = st.selectbox("🔍 Selecciona el Vehículo (Placa):", lista_placas)
        
        # Usamos columnas para que se vea ordenado
        col1, col2 = st.columns(2)
        with col1:
            hora_ingreso = st.text_input("Hora de Ingreso (ej. 08:30 AM):")
        with col2:
            hora_salida = st.text_input("Hora de Salida (ej. 05:00 PM):")
            
        actualizar = st.form_submit_button("Guardar Tiempos")

        if actualizar:
            # 1. Encontramos en qué fila de Google Sheets está esta placa.
            # (Sumamos +2 porque los índices de DataFrame empiezan en 0 y Sheets empieza en la fila 1 que tiene el encabezado)
            fila_indice = df.index[df['Placa'].astype(str) == placa_seleccionada].tolist()[0] + 2
            
            # 2. Actualizamos las celdas específicas en Google Sheets (Columna 4 es D, Columna 5 es E)
            if hora_ingreso:
                hoja_datos.update_cell(fila_indice, 4, hora_ingreso)
            if hora_salida:
                hoja_datos.update_cell(fila_indice, 5, hora_salida)
                
            st.success(f"⏱️ Tiempos actualizados para la placa {placa_seleccionada}.")
            st.rerun() # Recarga la página para mostrar los datos actualizados
else:
    st.info("Primero agrega un vehículo en el paso 1 para poder registrar sus tiempos.")

# --- 5. Mostrar la tabla de registros ---
st.subheader("3. Registros Actuales")
if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No hay vehículos registrados aún.")
