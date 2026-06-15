import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import json
from datetime import datetime
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Mi Ecosistema Financiero", page_icon="📊", layout="wide")

# --- NUEVO: CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    # Lee la llave secreta que guardaste en Streamlit
    credenciales_json = st.secrets["GOOGLE_CREDENTIALS"]
    creds_dict = json.loads(credenciales_json)
    
    # Se conecta a Google usando tu bot
    gc = gspread.service_account_from_dict(creds_dict)
    
    # Abre exactamente tu archivo (el nombre debe coincidir con el título de tu Excel)
    sh = gc.open("Base_Finanzas_2026")
    return sh.sheet1

hoja = conectar_sheets()

# 2. FUNCIONES PARA LEER Y GUARDAR EN LA NUBE
def cargar_datos():
    datos = hoja.get_all_records()
    if len(datos) > 0:
        df = pd.DataFrame(datos)
        
        # --- EL ESCUDO PROTECTOR ---
        # Esto limpia cualquier espacio invisible al principio o final de tus títulos
        df.columns = df.columns.str.strip() 
        
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df
    else:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Categoría", "Monto", "Descripción"])
        
def guardar_registro(fecha, tipo, categoria, monto, descripcion):
    # Escribe la fila directamente en el Excel de tu Google Drive
    hoja.append_row([str(fecha), tipo, categoria, monto, descripcion])

def borrar_ultimo_registro(df):
    datos = hoja.get_all_records()
    if len(datos) > 0:
        # Calcula la última fila (+1 por el encabezado, +1 porque gspread cuenta desde 1)
        fila_a_borrar = len(datos) + 1
        hoja.delete_rows(fila_a_borrar)

df = cargar_datos()

# 3. BARRA LATERAL (PANEL OPERATIVO)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/YPF_logo.svg/1200px-YPF_logo.svg.png", width=100)
st.sidebar.title("Panel Operativo")

# Filtro por Mes
if not df.empty:
    df['Mes-Año'] = df['Fecha'].dt.strftime('%m-%Y')
    meses_disponibles = ["Todos"] + list(df['Mes-Año'].dropna().unique())
    mes_seleccionado = st.sidebar.selectbox("📅 Mes a Analizar", meses_disponibles)
    df_filtrado = df[df['Mes-Año'] == mes_seleccionado] if mes_seleccionado != "Todos" else df
else:
    df_filtrado = df
    st.sidebar.info("Cargá datos para habilitar filtros.")

# --- NUEVO: OBTENCIÓN AUTOMÁTICA DEL DÓLAR BLUE ---
@st.cache_data(ttl=3600) # Actualiza el valor cada 1 hora (3600 segundos)
def obtener_dolar_blue():
    try:
        url = "https://dolarapi.com/v1/dolares/blue"
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        return float(datos["venta"]) # Usamos el precio de venta
    except:
        return 1200.0 # Valor de rescate por si la API se cae algún día

dolar_hoy = obtener_dolar_blue()

# Conversor Bimonetario Automático
cotizacion_usd = st.sidebar.number_input("Cotización Dólar Blue (ARS)", min_value=500.0, value=dolar_hoy, step=10.0)
st.sidebar.caption("🔄 Actualizado automáticamente via DolarApi")
st.sidebar.markdown("---")

# Formulario de carga
with st.sidebar.form("formulario_movimientos", clear_on_submit=True):
    st.subheader("➕ Nuevo Registro")
    fecha = st.date_input("Fecha", datetime.today())
    tipo = st.selectbox("Tipo", ["Egreso", "Ingreso"])
    
    if tipo == "Ingreso":
        categoria = st.selectbox("Categoría", ["YPF (Sueldo/Bono)", "Negocio e Inversiones", "Otros Ingresos"])
    else:
        categoria = st.selectbox("Categoría", [
            "Costos Fijos (Alquiler/Servicios)", 
            "Salidas y Joda", 
            "Compras Buenas (Valor/Bienestar)", 
            "Compras Malas (Impulso/Arrepentimiento)", 
            "Mantenimiento Moto / Nafta",
            "Suscripciones (Netflix/Gym)",
            "Proyecto Moto XR250", 
            "Ahorro / Interlagos F1"
        ])
        
    monto = st.number_input("Monto (ARS)", min_value=0.0, step=1000.0, format="%.2f")
    descripcion = st.text_input("Descripción breve")
    
    boton_guardar = st.form_submit_button("Guardar Movimiento")
    
    if boton_guardar and monto > 0:
        guardar_registro(fecha, tipo, categoria, monto, descripcion)
        st.success("¡Guardado en Google Drive correctamente!")
        st.rerun()

# Herramientas
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Herramientas")
if st.sidebar.button("🗑️ Borrar último registro"):
    if not df.empty:
        borrar_ultimo_registro(df)
        st.success("Último registro eliminado.")
        st.rerun()

if not df.empty:
    csv = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(label="📥 Descargar a Excel (CSV)", data=csv, file_name='exportacion.csv', mime='text/csv')

# 4. PANTALLA PRINCIPAL DIVIDIDA EN PESTAÑAS (TABS)
st.title("📊 Ecosistema Financiero")
tab_dashboard, tab_historial, tab_metas = st.tabs(["📈 Dashboard y Análisis", "📝 Historial de Movimientos", "🎯 Mis Metas"])

# --- PESTAÑA 1: DASHBOARD ---
with tab_dashboard:
    ingresos_totales = df_filtrado[df_filtrado["Tipo"] == "Ingreso"]["Monto"].sum()
    egresos_totales = df_filtrado[df_filtrado["Tipo"] == "Egreso"]["Monto"].sum()
    saldo_actual = ingresos_totales - egresos_totales
    saldo_usd = saldo_actual / cotizacion_usd if cotizacion_usd > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos", f"${ingresos_totales:,.0f}")
    col2.metric("Egresos", f"${egresos_totales:,.0f}")
    col3.metric("Saldo Disponible", f"${saldo_actual:,.0f}")
    col4.metric("Saldo en USD", f"US$ {saldo_usd:,.0f}")

    st.markdown("---")
    
    if not df_filtrado.empty and egresos_totales > 0:
        st.subheader("🧠 Inteligencia Financiera")
        cat_fijos = ["Costos Fijos (Alquiler/Servicios)", "Suscripciones (Netflix/Gym)", "Mantenimiento Moto / Nafta"]
        cat_ahorro = ["Proyecto Moto XR250", "Ahorro / Interlagos F1"]
        
        df_egresos = df_filtrado[df_filtrado["Tipo"] == "Egreso"]
        gasto_fijo = df_egresos[df_egresos["Categoría"].isin(cat_fijos)]["Monto"].sum()
        gasto_ahorro = df_egresos[df_egresos["Categoría"].isin(cat_ahorro)]["Monto"].sum()
        gasto_variable = egresos_totales - gasto_fijo - gasto_ahorro
        
        tasa_ahorro = (gasto_ahorro / ingresos_totales * 100) if ingresos_totales > 0 else 0
        
        col_tasa, col_regla = st.columns([1, 2])
        
        with col_tasa:
            st.info(f"**Tasa de Ahorro:** {tasa_ahorro:.1f}%")
            if tasa_ahorro >= 20:
                st.success("¡Excelente! Estás ahorrando/invirtiendo por encima del 20% recomendado.")
            elif tasa_ahorro > 0:
                st.warning("Estás ahorrando, pero intentá acercarte al 20%.")
            else:
                st.error("Alerta: No estás registrando ahorros este mes.")
                
        with col_regla:
            st.markdown("**Regla 50/30/20 (Fijos / Variables / Ahorro)**")
            pct_fijo = (gasto_fijo / ingresos_totales * 100) if ingresos_totales > 0 else 0
            pct_var = (gasto_variable / ingresos_totales * 100) if ingresos_totales > 0 else 0
            st.progress(min(pct_fijo / 50, 1.0), text=f"Fijos ({pct_fijo:.1f}% - Ideal 50%)")
            st.progress(min(pct_var / 30, 1.0), text=f"Variables ({pct_var:.1f}% - Ideal 30%)")
            st.progress(min(tasa_ahorro / 20, 1.0), text=f"Ahorro ({tasa_ahorro:.1f}% - Ideal 20%)")

        st.markdown("---")

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown("**Distribución de Egresos**")
            fig_torta = px.pie(df_egresos, values="Monto", names="Categoría", hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig_torta, use_container_width=True)
            
        with col_graf2:
            st.markdown("**Balance General por Categoría**")
            df_agrupado = df_filtrado.groupby(["Categoría", "Tipo"])["Monto"].sum().reset_index()
            fig_barras = px.bar(df_agrupado, x="Categoría", y="Monto", color="Tipo", barmode="group",
                                color_discrete_map={"Ingreso": "#2a9d8f", "Egreso": "#e63946"})
            st.plotly_chart(fig_barras, use_container_width=True)

# --- PESTAÑA 2: HISTORIAL ---
with tab_historial:
    st.subheader("Registro de Movimientos")
    if not df_filtrado.empty:
        df_mostrar = df_filtrado.sort_values(by="Fecha", ascending=False).reset_index(drop=True)
        df_mostrar['Fecha'] = df_mostrar['Fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_mostrar, use_container_width=True)
    else:
        st.info("No hay movimientos registrados.")

# --- PESTAÑA 3: METAS ---
with tab_metas:
    st.subheader("🎯 Progreso de Objetivos 2026")
    
    OBJETIVO_MOTO = 3000000 
    OBJETIVO_F1 = 1500000
    
    total_moto = df[df["Categoría"] == "Proyecto Moto XR250"]["Monto"].sum()
    total_f1 = df[df["Categoría"] == "Ahorro / Interlagos F1"]["Monto"].sum()
    
    pct_moto = min(total_moto / OBJETIVO_MOTO, 1.0)
    pct_f1 = min(total_f1 / OBJETIVO_F1, 1.0)
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.info("🏍️ Proyecto Moto XR250")
        st.progress(pct_moto, text=f"${total_moto:,.0f} de ${OBJETIVO_MOTO:,.0f} ({pct_moto*100:.1f}%)")
    with col_m2:
        st.success("🏎️ Viaje Interlagos F1")
        st.progress(pct_f1, text=f"${total_f1:,.0f} de ${OBJETIVO_F1:,.0f} ({pct_f1*100:.1f}%)")
