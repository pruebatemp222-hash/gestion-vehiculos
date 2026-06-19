import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time 
import pytz

# --- 1. Configuración Profesional de la página ---
st.set_page_config(page_title="SHREK", layout="centered", page_icon="🅿️")

# --- CSS para Diseño Móvil de Alta Gama ---
st.markdown("""
    <style>
    div.stButton > button {
        width: 100% !important;
        height: 55px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    div.stButton > button:active { transform: scale(0.95); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f8f9fa;
        border-radius: 10px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🅿️ Control de Parqueo")

# --- 2. Conexión a Base de Datos (Con Historial Automático) ---
@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict)
    cliente = gspread.authorize(creds.with_scopes(["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    
    archivo = cliente.open("Vehiculos_App")
    hoja_principal = archivo.sheet1
    
    # Busca la pestaña "Historial". Si no existe, la crea automáticamente.
    try:
        hoja_hist = archivo.worksheet("Historial")
    except gspread.exceptions.WorksheetNotFound:
        hoja_hist = archivo.add_worksheet(title="Historial", rows="1000", cols="6")
        hoja_hist.append_row(["Fecha", "Placa", "Propietario", "Hora de Ingreso", "Hora de Salida", "Pago"])
        
    return hoja_principal, hoja_hist

try:
    hoja_datos, hoja_historial = conectar_sheets()
except Exception as e:
    st.error(f"❌ Error de conexión: {e}")
    st.stop()

# --- BLINDAJE CONTRA ERRORES DE LECTURA ---
try:
    datos = hoja_datos.get_all_records()
except Exception:
    datos = []

if datos:
    df = pd.DataFrame(datos)
    for col in ["Hora de Ingreso", "Hora de Salida", "Pago"]:
        if col not in df.columns:
            df[col] = ""
    df.fillna("", inplace=True)
else:
    df = pd.DataFrame()

# --- 3. Interfaz de Usuario ---
tab_control, tab_gestion, tab_historial = st.tabs(["⏱️ Panel", "⚙️ Gestión", "📅 Historial"])

# ==========================================
# PESTAÑA 1: PANEL DE ASISTENCIA Y COBROS 
# ==========================================
with tab_control:
    st.subheader("Control en Vivo")
    
    if not df.empty:
        lista_placas = df["Placa"].astype(str).tolist()
        placa_sel = st.selectbox("🔍 Selecciona un Vehículo:", lista_placas)
        
        # Validación extra por si la placa seleccionada no se encuentra en el DataFrame
        vehiculos_filtrados = df[df["Placa"].astype(str) == placa_sel]
        
        if not vehiculos_filtrados.empty:
            vehiculo = vehiculos_filtrados.iloc[0]
            fila_idx = df.index[df['Placa'].astype(str) == placa_sel].tolist()[0] + 2
            
            st.info(f"👤 **Propietario:** {vehiculo['Propietario']} | 🚗 **Placa:** {placa_sel}")
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Ingreso", vehiculo["Hora de Ingreso"] if vehiculo["Hora de Ingreso"] else "--:--")
            col_m2.metric("Salida", vehiculo["Hora de Salida"] if vehiculo["Hora de Salida"] else "--:--")
            col_m3.metric("Pago", vehiculo["Pago"] if vehiculo["Pago"] else "Pendiente 🔴")
            
            st.write("---")
            
            # Configuración de Hora Local
            zona_horaria = pytz.timezone('America/Lima') 
            hora_actual = datetime.now(zona_horaria).strftime("%H:%M")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🟢 Ingreso", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 4, hora_actual)
                    st.success(f"Ingreso: {hora_actual}")
                    time.sleep(1)
                    st.rerun()
                    
            with col2:
                if st.button("🔴 Salida", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 5, hora_actual)
                    st.success(f"Salida: {hora_actual}")
                    time.sleep(1)
                    st.rerun()
                    
            with col3:
                if st.button("💵 Pagó", type="primary", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 6, "Pagado ✅")
                    st.success("¡Pago registrado!")
                    time.sleep(1)
                    st.rerun()
                    
            st.write("---")
            # --- SISTEMA DE ARCHIVADO ---
            if st.button("📦 Archivar en Historial y Cerrar Día"):
                fecha_actual = datetime.now(zona_horaria).strftime("%d/%m/%Y")
                
                hoja_historial.append_row([
                    fecha_actual, 
                    placa_sel, 
                    vehiculo['Propietario'], 
                    vehiculo['Hora de Ingreso'], 
                    vehiculo['Hora de Salida'], 
                    vehiculo['Pago']
                ])
                
                hoja_datos.update_cell(fila_idx, 4, "")
                hoja_datos.update_cell(fila_idx, 5, "")
                hoja_datos.update_cell(fila_idx, 6, "Pendiente 🔴")
                
                st.success(f"✅ ¡Datos de {placa_sel} guardados en el historial!")
                time.sleep(1.5)
                st.rerun()
        else:
            st.warning("⚠️ No tiene resultados en la búsqueda.")

    else:
        st.warning("Agrega un vehículo en la pestaña 'Gestión'.")

# ==========================================
# PESTAÑA 2: GESTIÓN (AGREGAR / ELIMINAR)
# ==========================================
with tab_gestion:
    st.subheader("Registrar Nuevo")
    with st.form("form_nuevo", clear_on_submit=True):
        n_placa = st.text_input("Placa:").strip()
        n_prop = st.text_input("Propietario:").strip()
        if st.form_submit_button("Guardar Vehículo ➕"):
            if n_placa and n_prop:
                if not df.empty and n_placa.lower() in df["Placa"].astype(str).str.lower().values:
                    st.error("⚠️ La placa ya existe.")
                else:
                    nuevo_n = len(datos) + 1 if datos else 1
                    hoja_datos.append_row([nuevo_n, n_placa, n_prop, "", "", "Pendiente 🔴"])
                    st.success("✅ Vehículo guardado.")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Completa los datos.")
                
    st.write("---")
    st.subheader("Eliminar Registro")
    if not df.empty:
        placa_eliminar = st.selectbox("Seleccionar Placa para Borrar:", df["Placa"].astype(str).tolist())
        if st.button("Eliminar Vehículo 🗑️"):
            f_idx = df.index[df['Placa'].astype(str) == placa_eliminar].tolist()[0] + 2
            hoja_datos.delete_rows(f_idx)
            st.success("Vehículo eliminado.")
            time.sleep(1)
            st.rerun()

# ==========================================
# PESTAÑA 3: HISTORIAL MULTI-FILTRO (FECHA Y PLACA)
# ==========================================
with tab_historial:
    st.subheader("📅 Historial y Búsqueda")
    
    # --- BLINDAJE CONTRA ERRORES EN HISTORIAL ---
    try:
        datos_historial = hoja_historial.get_all_records()
    except Exception:
        datos_historial = []
    
    if datos_historial:
        df_hist = pd.DataFrame(datos_historial)
        
        # 1. Obtener listas únicas de Fechas y Placas
        fechas_unicas = ["Todas"] + df_hist["Fecha"].astype(str).unique().tolist()
        placas_unicas = ["Todas"] + df_hist["Placa"].astype(str).unique().tolist()
        
        col_filtro1, col_filtro2 = st.columns(2)
        
        with col_filtro1:
            fecha_seleccionada = st.selectbox("📅 Filtrar por Fecha:", fechas_unicas)
            
        with col_filtro2:
            placa_seleccionada_hist = st.selectbox("🚗 Filtrar por Placa:", placas_unicas)
            
        st.write("---")
        
        df_mostrar = df_hist.copy() 
        
        if fecha_seleccionada != "Todas":
            df_mostrar = df_mostrar[df_mostrar["Fecha"].astype(str) == fecha_seleccionada]
            
        if placa_seleccionada_hist != "Todas":
            df_mostrar = df_mostrar[df_mostrar["Placa"].astype(str) == placa_seleccionada_hist]
            
        # 4. Mostrar Resultados o Notificación de Vacío
        if not df_mostrar.empty:
            st.success(f"✅ Mostrando {len(df_mostrar)} resultados encontrados.")
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            # EL MENSAJE QUE SOLICITASTE
            st.warning("⚠️ No tiene resultados en la búsqueda.")
            
    else:
        st.info("Aún no has archivado ningún registro al finalizar el día.")
