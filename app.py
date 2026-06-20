import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time 
import pytz
import calendar

# --- 1. Configuración Profesional de la página ---
st.set_page_config(page_title="Gestión de Cochera", layout="centered", page_icon="🅿️")

# Inicializar Memoria de Sesión para navegación dinámica
if 'vista_inicio' not in st.session_state:
    st.session_state.vista_inicio = 'lista'
if 'vehiculo_detalle' not in st.session_state:
    st.session_state.vehiculo_detalle = None

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
    /* Estilo para las tarjetas de resumen */
    .tarjeta-resumen {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #0068c9;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🅿️ Control de Parqueo")

# --- 2. Conexión a Base de Datos (Con Historial y Abonos) ---
@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict)
    cliente = gspread.authorize(creds.with_scopes(["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    
    archivo = cliente.open("Vehiculos_App")
    hoja_principal = archivo.sheet1
    
    try:
        hoja_hist = archivo.worksheet("Historial")
    except gspread.exceptions.WorksheetNotFound:
        hoja_hist = archivo.add_worksheet(title="Historial", rows="1000", cols="6")
        hoja_hist.append_row(["Fecha", "Placa", "Propietario", "Hora de Ingreso", "Hora de Salida", "Pago"])
        
    try:
        hoja_abonos = archivo.worksheet("Abonos")
    except gspread.exceptions.WorksheetNotFound:
        hoja_abonos = archivo.add_worksheet(title="Abonos", rows="1000", cols="5")
        hoja_abonos.append_row(["Fecha", "Placa", "Propietario", "Descripción del Periodo", "Monto Pagado"])
        
    return hoja_principal, hoja_hist, hoja_abonos

try:
    hoja_datos, hoja_historial, hoja_abonos = conectar_sheets()
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

# Configuración de Hora Local Global
zona_horaria = pytz.timezone('America/Lima') 
hora_actual = datetime.now(zona_horaria).strftime("%H:%M")
fecha_actual = datetime.now(zona_horaria).strftime("%d/%m/%Y")
mes_actual_str = datetime.now(zona_horaria).strftime("%m/%Y")

# --- 3. Interfaz de Usuario ---
tab_inicio, tab_control, tab_gestion, tab_pagos, tab_historial = st.tabs(["🏠 Inicio", "⏱️ Panel", "⚙️ Gestión", "💰 Pagos", "📅 Historial"])

# ==========================================
# PESTAÑA 0: INICIO (DASHBOARD Y REPORTE MENSUAL)
# ==========================================
with tab_inicio:
    
    # VISTA 1: Lista Resumida de Vehículos
    if st.session_state.vista_inicio == 'lista':
        st.subheader("📊 Resumen de Clientes")
        if not df.empty:
            for idx, row in df.iterrows():
                # Tarjeta visual para cada cliente
                st.markdown(f"""
                <div class="tarjeta-resumen">
                    <h4 style='margin:0; color:#333;'>👤 {row['Propietario']}</h4>
                    <p style='margin:0; color:#666;'>🚗 Placa: {row['Placa']} | Estado Hoy: {row['Pago'] if row['Pago'] else 'Sin Ingreso'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón para entrar al detalle
                if st.button(f"🔍 Ver Reporte Mensual", key=f"btn_rep_{row['Placa']}"):
                    st.session_state.vehiculo_detalle = row['Placa']
                    st.session_state.vista_inicio = 'detalle'
                    st.rerun()
                st.write("---")
        else:
            st.info("No hay vehículos registrados en el sistema.")

    # VISTA 2: Perfil y Reporte Detallado del Vehículo
    elif st.session_state.vista_inicio == 'detalle':
        if st.button("⬅️ Volver al Resumen General"):
            st.session_state.vista_inicio = 'lista'
            st.session_state.vehiculo_detalle = None
            st.rerun()
            
        placa_det = st.session_state.vehiculo_detalle
        vehiculo_det = df[df["Placa"].astype(str) == placa_det].iloc[0]
        
        st.subheader(f"Reporte: {vehiculo_det['Propietario']} ({placa_det})")
        
        # Traer el historial completo para cálculos
        try:
            datos_hist_total = hoja_historial.get_all_records()
            df_hist_total = pd.DataFrame(datos_hist_total) if datos_hist_total else pd.DataFrame()
        except:
            df_hist_total = pd.DataFrame()

        # Filtrar solo el historial de este vehículo
        if not df_hist_total.empty:
            df_vehiculo = df_hist_total[df_hist_total["Placa"].astype(str) == placa_det]
        else:
            df_vehiculo = pd.DataFrame()

        # Generador de Meses
        opciones_meses = [mes_actual_str]
        if not df_vehiculo.empty:
            # Extraer meses únicos del historial de esta persona
            df_vehiculo["Mes_Anio"] = pd.to_datetime(df_vehiculo["Fecha"], format="%d/%m/%Y", errors="coerce").dt.strftime("%m/%Y")
            meses_historial = df_vehiculo["Mes_Anio"].dropna().unique().tolist()
            opciones_meses = sorted(list(set(opciones_meses + meses_historial)), reverse=True)
            
        mes_seleccionado = st.selectbox("📅 Selecciona el Mes a Evaluar:", opciones_meses)
        
        st.write("---")
        st.write("**Detalle Diario de Asistencia y Pagos:**")
        
        # Lógica para construir el reporte del mes
        mes, anio = mes_seleccionado.split("/")
        dias_del_mes = calendar.monthrange(int(anio), int(mes))[1]
        
        # Si el mes seleccionado es el actual, evaluamos solo hasta el día de hoy para no mostrar "No vino" en el futuro
        hoy_dt = datetime.now(zona_horaria)
        if int(mes) == hoy_dt.month and int(anio) == hoy_dt.year:
            limite_dias = hoy_dt.day
        else:
            limite_dias = dias_del_mes
            
        reporte_mensual = []
        pagados = 0
        deudas = 0
        faltas = 0
        
        for dia in range(1, limite_dias + 1):
            fecha_str = f"{dia:02d}/{mes}/{anio}"
            
            # Buscar si hay registro de esta fecha en el historial del vehículo
            if not df_vehiculo.empty:
                registro_dia = df_vehiculo[df_vehiculo["Fecha"] == fecha_str]
            else:
                registro_dia = pd.DataFrame()
                
            if not registro_dia.empty:
                # Tomamos el último registro de ese día por si entró varias veces
                estado_pago = registro_dia.iloc[-1]["Pago"]
                reporte_mensual.append({"Fecha": fecha_str, "Asistencia": "Vino 🚗", "Estado": estado_pago})
                if "Pagado" in estado_pago:
                    pagados += 1
                else:
                    deudas += 1
            else:
                reporte_mensual.append({"Fecha": fecha_str, "Asistencia": "No vino ⚪", "Estado": "-"})
                faltas += 1
                
        # Mostrar las métricas del mes en tarjetas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("✅ Días Pagados", pagados)
        col_m2.metric("❌ Deudas/Pendientes", deudas)
        col_m3.metric("⚪ Días que No Vino", faltas)
        
        # Mostrar tabla detallada del mes
        st.dataframe(pd.DataFrame(reporte_mensual), use_container_width=True, hide_index=True)


# ==========================================
# PESTAÑA 1: PANEL DE ASISTENCIA Y COBROS
# ==========================================
with tab_control:
    st.subheader("Control en Vivo")
    
    if not df.empty:
        df['Buscar_Propietario'] = df["Propietario"].astype(str) + " — " + df["Placa"].astype(str)
        lista_propietarios = df["Buscar_Propietario"].tolist()
        
        propietario_sel = st.selectbox("🔍 Selecciona un Propietario:", lista_propietarios, key="panel_propietario")
        vehiculos_filtrados = df[df["Buscar_Propietario"] == propietario_sel]
        
        if not vehiculos_filtrados.empty:
            vehiculo = vehiculos_filtrados.iloc[0]
            placa_sel = vehiculo['Placa']
            fila_idx = df.index[df['Buscar_Propietario'] == propietario_sel].tolist()[0] + 2
            
            st.info(f"👤 **Propietario:** {vehiculo['Propietario']} | 🚗 **Placa:** {placa_sel}")
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Ingreso", vehiculo["Hora de Ingreso"] if vehiculo["Hora de Ingreso"] else "--:--")
            col_m2.metric("Salida", vehiculo["Hora de Salida"] if vehiculo["Hora de Salida"] else "--:--")
            col_m3.metric("Pago", vehiculo["Pago"] if vehiculo["Pago"] else "Pendiente 🔴")
            
            st.write("---")
            
            if vehiculo["Hora de Ingreso"] != "" and vehiculo["Pago"] == "Pendiente 🔴":
                st.warning("⚠️ RECORDATORIO: Este vehículo aún tiene un PAGO PENDIENTE.")
            elif vehiculo["Pago"] == "No Pagó ❌":
                st.error("🚨 ALERTA: Este vehículo registra una DEUDA de su visita.")
            
            col1, col2 = st.columns(2)
            col3, col4 = st.columns(2)
            
            with col1:
                if st.button("🟢 Ingreso", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 4, hora_actual)
                    hoja_datos.update_cell(fila_idx, 5, "")
                    hoja_datos.update_cell(fila_idx, 6, "Pendiente 🔴")
                    hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], hora_actual, "", "Pendiente 🔴"])
                    st.success(f"✅ Ingreso actualizado.")
                    time.sleep(1)
                    st.rerun()
                    
            with col2:
                if st.button("🔴 Salida", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 5, hora_actual)
                    hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], hora_actual, vehiculo['Pago']])
                    st.success(f"✅ Salida actualizada.")
                    time.sleep(1)
                    st.rerun()
                    
            with col3:
                if st.button("💵 Pagó", type="primary", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 6, "Pagado ✅")
                    hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], vehiculo['Hora de Salida'], "Pagado ✅"])
                    st.success("✅ Pago registrado.")
                    time.sleep(1)
