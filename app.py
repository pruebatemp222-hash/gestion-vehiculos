import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Configuración de la página (Debe ser el primer comando) ---
st.set_page_config(page_title="Gestión Vehículos", layout="centered", page_icon="🚗")

# --- CSS Personalizado para Optimización Móvil (Touch-Friendly) ---
st.markdown("""
    <style>
    /* Hacer que todos los botones de envío ocupen el 100% del ancho del celular */
    div.stButton > button {
        width: 100% !important;
        height: 50px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        margin-top: 10px;
    }
    /* Estilizar la barra de pestañas para que parezcan botones de menú móvil */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        width: 100%;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 0px 12px;
        font-weight: bold;
        font-size: 14px;
        flex-grow: 1;
        text-align: center;
    }
    /* Cambiar el color del input en foco para pantallas móviles */
    input {
        font-size: 16px !important; /* Evita que iOS haga zoom automático molesto */
    }
    </style>
""", unsafe_allow_html=True)

st.title("Gestión de Vehículos 🚗")

# --- 2. Conexión a Google Sheets ---
@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["gcp_service_account"])
    # Ajuste para procesar correctamente los saltos de línea de la clave privada
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    cliente = gspread.authorize(creds.with_scopes(scopes))
    return cliente.open("Vehiculos_App").sheet1

try:
    hoja_datos = conectar_sheets()
except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.stop()

# Traemos la información fresca desde Google Sheets
datos = hoja_datos.get_all_records()
df = pd.DataFrame(datos) if datos else pd.DataFrame()

# --- 3. Organización de la Interfaz en "Botones" de Pestaña ---
# En un celular, estas pestañas se expanden horizontalmente ocupando todo el ancho de la pantalla
tab_agregar, tab_eliminar, tab_tiempos = st.tabs(["➕ Agregar", "❌ Eliminar", "📋 Lista / Horas"])

# --- PESTAÑA: AGREGAR VEHÍCULO ---
with tab_agregar:
    st.subheader("Agregar Nuevo Vehículo")
    with st.form("form_vehiculo", clear_on_submit=True):
        placa = st.text_input("Placa del Vehículo:").strip()
        propietario = st.text_input("Nombre del Propietario:").strip()
        
        # Botón grande ideal para pantallas táctiles
        enviado = st.form_submit_button("Confirmar Registro ➕")

        if enviado:
            if placa and propietario:
                # Evitar que registren la misma placa duplicada
                if not df.empty and placa.lower() in df["Placa"].astype(str).str.lower().values:
                    st.error(f"⚠️ La placa '{placa}' ya está registrada en el sistema.")
                else:
                    nuevo_numero = len(datos) + 1 if datos else 1
                    # Añadimos los campos base y dejamos las horas vacías para rellenar después
                    hoja_datos.append_row([nuevo_numero, placa, propietario, "", ""])
                    st.success(f"✅ ¡Vehículo {placa} guardado con éxito!")
                    st.rerun()
            else:
                st.warning("⚠️ Completa los dos campos de texto.")

# --- PESTAÑA: ELIMINAR VEHÍCULO ---
with tab_eliminar:
    st.subheader("Eliminar Vehículo del Sistema")
    if not df.empty:
        lista_placas = df["Placa"].astype(str).tolist()
        # Lista desplegable nativa móvil para seleccionar de forma rápida con el dedo
        placa_a_eliminar = st.selectbox("Selecciona la Placa a dar de baja:", lista_placas)
        
        # Mostrar a quién pertenece antes de borrar para evitar accidentes
        info_v = df[df["Placa"].astype(str) == placa_a_eliminar].iloc[0]
        st.error(f"⚠️ Atención: Vas a eliminar el vehículo de **{info_v['Propietario']}**")
        
        with st.form("form_eliminar"):
            confirmar_eliminar = st.form_submit_button("Confirmar Eliminar 🗑️")
            
            if confirmar_eliminar:
                # Buscamos el índice real en la hoja (+2 por cabecera y desfase de índice)
                fila_indice = df.index[df['Placa'].astype(str) == placa_a_eliminar].tolist()[0] + 2
                hoja_datos.delete_rows(fila_indice)
                st.success(f"🗑️ Registro de la placa {placa_a_eliminar} borrado completamente.")
                st.rerun()
    else:
        st.info("No hay vehículos registrados para poder eliminar.")

# --- PESTAÑA: LISTA GENERAL Y CONTROL DE TIEMPOS ---
with tab_tiempos:
    st.subheader("Control de Ingresos y Salidas")
    if not df.empty:
        lista_placas_t = df["Placa"].astype(str).tolist()
        placa_seleccionada = st.selectbox("Buscar Vehículo por Placa:", lista_placas_t, key="sb_tiempos")
        
        with st.form("form_tiempos"):
            hora_ingreso = st.text_input("Hora de Ingreso (ej: 07:15):")
            hora_salida = st.text_input("Hora de Salida (ej: 18:00):")
            actualizar = st.form_submit_button("Guardar Horarios ⏱️")

            if actualizar:
                fila_indice = df.index[df['Placa'].astype(str) == placa_seleccionada].tolist()[0] + 2
                if hora_ingreso:
                    hoja_datos.update_cell(fila_indice, 4, hora_ingreso) # Columna D
                if hora_salida:
                    hoja_datos.update_cell(fila_indice, 5, hora_salida) # Columna E
                    
                st.success(f"⏱️ Horarios guardados para la placa {placa_seleccionada}.")
                st.rerun()
                
        st.write("---")
        st.subheader("📋 Tabla de Registros en la Nube")
        # st.dataframe se adapta perfectamente al ancho de las pantallas de celular
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay vehículos para mostrar o registrar tiempos.")
