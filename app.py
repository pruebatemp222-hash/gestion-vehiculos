import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time 
import pytz
import calendar
import plotly.express as px

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

# --- 2. Conexión a Base de Datos ---
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

# --- BLINDAJE Y LIMPIEZA GLOBAL DE DATOS ---
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
    
    # Limpieza automática de espacios invisibles para evitar IndexErrors
    if "Placa" in df.columns:
        df["Placa"] = df["Placa"].astype(str).str.strip()
    if "Propietario" in df.columns:
        df["Propietario"] = df["Propietario"].astype(str).str.strip()
else:
    df = pd.DataFrame()

# Configuración de Hora Local Global
zona_horaria = pytz.timezone('America/Lima') 
hora_actual = datetime.now(zona_horaria).strftime("%H:%M")
fecha_actual = datetime.now(zona_horaria).strftime("%d/%m/%Y")
mes_actual_str = datetime.now(zona_horaria).strftime("%m/%Y")

# --- 3. Interfaz de Usuario (Tabs) ---
tab_inicio, tab_control, tab_gestion, tab_pagos, tab_historial = st.tabs(["🏠 Inicio", "⏱️ Panel", "⚙️ Gestión", "💰 Pagos", "📅 Historial"])

# ==========================================
# PESTAÑA 0: INICIO (DASHBOARD)
# ==========================================
with tab_inicio:
    if st.session_state.vista_inicio == 'lista':
        st.subheader("📊 Resumen de Clientes")
        if not df.empty:
            for idx, row in df.iterrows():
                st.markdown(f"""
                <div class="tarjeta-resumen">
                    <h4 style='margin:0; color:#333;'>👤 {row['Propietario']}</h4>
                    <p style='margin:0; color:#666;'>🚗 Placa: {row['Placa']} | Estado Hoy: {row['Pago'] if row['Pago'] else 'Sin Ingreso'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🔍 Ver Reporte Mensual", key=f"btn_rep_{row['Placa']}"):
                    st.session_state.vehiculo_detalle = row['Placa']
                    st.session_state.vista_inicio = 'detalle'
                    st.rerun()
                st.write("---")
        else:
            st.info("No hay vehículos registrados en el sistema.")

    elif st.session_state.vista_inicio == 'detalle':
        if st.button("⬅️ Volver al Resumen General"):
            st.session_state.vista_inicio = 'lista'
            st.session_state.vehiculo_detalle = None
            st.rerun()
            
        # Control estricto contra IndexErrors y espacios huérfanos
        placa_det = str(st.session_state.vehiculo_detalle).strip()
        filtro_vehiculo = df[df["Placa"] == placa_det] if not df.empty else pd.DataFrame()
        
        if not filtro_vehiculo.empty:
            vehiculo_det = filtro_vehiculo.iloc[0]
            propietario_nombre = vehiculo_det['Propietario']
        else:
            propietario_nombre = "Usuario"
            
        st.subheader(f"Reporte: {propietario_nombre} ({placa_det})")
        
        try:
            datos_hist_total = hoja_historial.get_all_records()
            df_hist_total = pd.DataFrame(datos_hist_total) if datos_hist_total else pd.DataFrame()
            if not df_hist_total.empty:
                if "Placa" in df_hist_total.columns:
                    df_hist_total["Placa"] = df_hist_total["Placa"].astype(str).str.strip()
                if "Fecha" in df_hist_total.columns:
                    df_hist_total["Fecha"] = df_hist_total["Fecha"].astype(str).str.strip()
        except:
            df_hist_total = pd.DataFrame()

        if not df_hist_total.empty:
            df_vehiculo = df_hist_total[df_hist_total["Placa"] == placa_det]
        else:
            df_vehiculo = pd.DataFrame()

        opciones_meses = [mes_actual_str]
        if not df_vehiculo.empty:
            df_vehiculo["Mes_Anio"] = pd.to_datetime(df_vehiculo["Fecha"], format="%d/%m/%Y", errors="coerce").dt.strftime("%m/%Y")
            meses_historial = df_vehiculo["Mes_Anio"].dropna().unique().tolist()
            opciones_meses = sorted(list(set(opciones_meses + meses_historial)), reverse=True)
            
        mes_seleccionado = st.selectbox("📅 Selecciona el Mes a Evaluar:", opciones_meses)
        st.write("---")
        
        mes, anio = mes_seleccionado.split("/")
        dias_del_mes = calendar.monthrange(int(anio), int(mes))[1]
        
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
            
            if not df_vehiculo.empty:
                registro_dia = df_vehiculo[df_vehiculo["Fecha"] == fecha_str]
            else:
                registro_dia = pd.DataFrame()
                
            if not registro_dia.empty:
                estado_pago = registro_dia.iloc[-1]["Pago"]
                reporte_mensual.append({"Fecha": fecha_str, "Asistencia": "Vino 🚗", "Estado": estado_pago})
                if "Pagado" in estado_pago:
                    pagados += 1
                else:
                    deudas += 1
            else:
                reporte_mensual.append({"Fecha": fecha_str, "Asistencia": "No vino ⚪", "Estado": "-"})
                faltas += 1
                
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("✅ Días Pagados", pagados)
        col_m2.metric("❌ Deudas/Pendientes", deudas)
        col_m3.metric("⚪ Días que No Vino", faltas)
        st.write("---")
        
        col_tabla, col_grafico = st.columns([1.5, 1.2]) 
        
        with col_tabla:
            st.write("📄 **Registro Detallado**")
            st.dataframe(pd.DataFrame(reporte_mensual), use_container_width=True, hide_index=True)
            
        with col_grafico:
            st.write("📊 **Distribución Mensual**")
            datos_grafico = pd.DataFrame({
                "Estado": ["Pagado", "Deuda", "Faltas"],
                "Días": [pagados, deudas, faltas]
            })
            datos_grafico = datos_grafico[datos_grafico["Días"] > 0]
            
            if not datos_grafico.empty:
                fig = px.pie(
                    datos_grafico, 
                    values="Días", 
                    names="Estado", 
                    hole=0.45, 
                    color="Estado",
                    color_discrete_map={
                        "Pagado": "#198754", 
                        "Deuda": "#dc3545",  
                        "Faltas": "#adb5bd"  
                    }
                )
                fig.update_layout(
                    margin=dict(t=20, b=20, l=0, r=0), 
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aún no hay datos para graficar este mes.")

# ==========================================
# PESTAÑA 1: PANEL DE ASISTENCIA (SINCRONIZADO)
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
                    
                    # Crea registro nuevo únicamente al marcar Ingreso
                    hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], hora_actual, "", "Pendiente 🔴"])
                    
                    st.success(f"✅ Ingreso actualizado.")
                    time.sleep(1)
                    st.rerun()
                    
            with col2:
                if st.button("🔴 Salida", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 5, hora_actual)
                    
                    try:
                        datos_h = hoja_historial.get_all_records()
                        df_h = pd.DataFrame(datos_h) if datos_h else pd.DataFrame()
                        if not df_h.empty:
                            df_h['Fecha'] = df_h['Fecha'].astype(str).str.strip()
                            df_h['Placa'] = df_h['Placa'].astype(str).str.strip()
                            filtro = (df_h['Fecha'] == fecha_actual) & (df_h['Placa'] == str(placa_sel).strip())
                            
                            if not df_h[filtro].empty:
                                last_idx = df_h.index[filtro].tolist()[-1] + 2
                                hoja_historial.update_cell(last_idx, 5, hora_actual)
                            else:
                                hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], hora_actual, vehiculo['Pago']])
                        else:
                            hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], hora_actual, vehiculo['Pago']])
                    except: pass
                    
                    st.success(f"✅ Salida actualizada.")
                    time.sleep(1)
                    st.rerun()
                    
            with col3:
                if st.button("💵 Pagó", type="primary", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 6, "Pagado ✅")
                    
                    try:
                        datos_h = hoja_historial.get_all_records()
                        df_h = pd.DataFrame(datos_h) if datos_h else pd.DataFrame()
                        if not df_h.empty:
                            df_h['Fecha'] = df_h['Fecha'].astype(str).str.strip()
                            df_h['Placa'] = df_h['Placa'].astype(str).str.strip()
                            filtro = (df_h['Fecha'] == fecha_actual) & (df_h['Placa'] == str(placa_sel).strip())
                            
                            if not df_h[filtro].empty:
                                last_idx = df_h.index[filtro].tolist()[-1] + 2
                                hoja_historial.update_cell(last_idx, 6, "Pagado ✅")
                            else:
                                hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], vehiculo['Hora de Salida'], "Pagado ✅"])
                        else:
                            hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], vehiculo['Hora de Salida'], "Pagado ✅"])
                    except: pass
                    
                    st.success("✅ Pago registrado.")
                    time.sleep(1)
                    st.rerun()
                    
            with col4:
                if st.button("❌ No Pagó", use_container_width=True):
                    hoja_datos.update_cell(fila_idx, 6, "No Pagó ❌")
                    
                    try:
                        datos_h = hoja_historial.get_all_records()
                        df_h = pd.DataFrame(datos_h) if datos_h else pd.DataFrame()
                        if not df_h.empty:
                            df_h['Fecha'] = df_h['Fecha'].astype(str).str.strip()
                            df_h['Placa'] = df_h['Placa'].astype(str).str.strip()
                            filtro = (df_h['Fecha'] == fecha_actual) & (df_h['Placa'] == str(placa_sel).strip())
                            
                            if not df_h[filtro].empty:
                                last_idx = df_h.index[filtro].tolist()[-1] + 2
                                hoja_historial.update_cell(last_idx, 6, "No Pagó ❌")
                            else:
                                hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], vehiculo['Hora de Salida'], "No Pagó ❌"])
                        else:
                            hoja_historial.append_row([fecha_actual, placa_sel, vehiculo['Propietario'], vehiculo['Hora de Ingreso'], vehiculo['Hora de Salida'], "No Pagó ❌"])
                    except: pass
                    
                    st.error("❌ Deuda registrada.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.warning("⚠️ No tiene resultados en la búsqueda.")
    else:
        st.warning("Agrega un vehículo en 'Gestión'.")

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
        df['Buscar_Propietario'] = df["Propietario"].astype(str) + " — " + df["Placa"].astype(str)
        prop_eliminar = st.selectbox("Seleccionar Propietario para Borrar:", df["Buscar_Propietario"].tolist())
        if st.button("Eliminar Vehículo 🗑️"):
            f_idx = df.index[df['Buscar_Propietario'] == prop_eliminar].tolist()[0] + 2
            hoja_datos.delete_rows(f_idx)
            st.success("Vehículo eliminado.")
            time.sleep(1)
            st.rerun()

# ==========================================
# PESTAÑA 3: PAGOS MÚLTIPLES (POR DÍAS/SEMANAS)
# ==========================================
with tab_pagos:
    st.subheader("Abonos Adelantados o Atrasados")
    if not df.empty:
        df['Buscar_Propietario'] = df["Propietario"].astype(str) + " — " + df["Placa"].astype(str)
        with st.form("form_pagos", clear_on_submit=True):
            propietario_pago_sel = st.selectbox("👤 Propietario:", df["Buscar_Propietario"].tolist())
            st.write("📅 **Selecciona los días a pagar:**")
            fechas_pago = st.date_input("Haz clic para elegir Inicio y Fin (o un solo día):", value=[], format="DD/MM/YYYY")
            monto = st.number_input("💰 Monto Pagado:", min_value=0.0, step=1.0, format="%.2f")
            
            if st.form_submit_button("Registrar Pago Múltiple 💵"):
                descripcion_generada = ""
                if isinstance(fechas_pago, tuple) or isinstance(fechas_pago, list):
                    if len(fechas_pago) == 2:
                        dias_total = (fechas_pago[1] - fechas_pago[0]).days + 1
                        descripcion_generada = f"Del {fechas_pago[0].strftime('%d/%m/%Y')} al {fechas_pago[1].strftime('%d/%m/%Y')} ({dias_total} días)"
                    elif len(fechas_pago) == 1:
                        descripcion_generada = f"Día: {fechas_pago[0].strftime('%d/%m/%Y')}"
                elif fechas_pago:
                    descripcion_generada = f"Día: {fechas_pago.strftime('%d/%m/%Y')}"

                if descripcion_generada and monto > 0:
                    vehiculo_sel = df[df["Buscar_Propietario"] == propietario_pago_sel].iloc[0]
                    hoja_abonos.append_row([fecha_actual, vehiculo_sel["Placa"], vehiculo_sel["Propietario"], descripcion_generada, monto])
                    st.success(f"✅ Pago registrado.")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("⚠️ Selecciona fecha y monto.")
                    
        st.write("---")
        try:
            datos_abonos = hoja_abonos.get_all_records()
        except Exception:
            datos_abonos = []
            
        if datos_abonos:
            df_abonos = pd.DataFrame(datos_abonos)
            st.dataframe(df_abonos, use_container_width=True)
            lista_opciones_abono = [f"Fila {idx + 2} | {row['Fecha']} - {row['Propietario']} ({row['Placa']}) - S/{row['Monto Pagado']}" for idx, row in df_abonos.iterrows()]
            abono_a_eliminar = st.selectbox("Anular pago:", lista_opciones_abono)
            
            if st.button("❌ Eliminar Este Pago"):
                fila_abono_idx = int(abono_a_eliminar.split("|")[0].replace("Fila", "").strip())
                hoja_abonos.delete_rows(fila_abono_idx)
                st.success("✅ Pago eliminado.")
                time.sleep(1)
                st.rerun()

# ==========================================
# PESTAÑA 4: HISTORIAL MULTI-FILTRO (DIARIO)
# ==========================================
with tab_historial:
    st.subheader("📅 Historial General Diario")
    try:
        datos_historial = hoja_historial.get_all_records()
    except Exception:
        datos_historial = []
    
    if datos_historial:
        df_hist = pd.DataFrame(datos_historial)
        
        # Limpieza de espacios en filtros del historial para máxima estabilidad
        for c in ["Fecha", "Placa", "Propietario"]:
            if c in df_hist.columns:
                df_hist[c] = df_hist[c].astype(str).str.strip()
                
        fechas_unicas = ["Todas"] + df_hist["Fecha"].unique().tolist()
        propietarios_unicos = ["Todas"] + df_hist["Propietario"].unique().tolist()
        
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            fecha_seleccionada = st.selectbox("📅 Fecha:", fechas_unicas)
        with col_filtro2:
            prop_seleccionado_hist = st.selectbox("👤 Propietario:", propietarios_unicos, key="hist_prop")
            
        df_mostrar = df_hist.copy() 
        if fecha_seleccionada != "Todas":
            df_mostrar = df_mostrar[df_mostrar["Fecha"] == fecha_seleccionada]
        if prop_seleccionado_hist != "Todas":
            df_mostrar = df_mostrar[df_mostrar["Propietario"] == prop_seleccionado_hist]
            
        if not df_mostrar.empty:
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No hay resultados.")
    else:
        st.info("Aún no hay historial.")
