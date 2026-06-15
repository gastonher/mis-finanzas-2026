import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import json
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Mi Ecosistema Financiero", page_icon="📊", layout="wide")

# --- CONEXIÓN INTEGRAL A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    credenciales_json = st.secrets["GOOGLE_CREDENTIALS"]
    creds_dict = json.loads(credenciales_json)
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open("Base_Finanzas_2026")
    return sh

sh = conectar_sheets()
hoja = sh.sheet1

# [NUEVO] Inicialización automática de la pestaña de Metas si no existe
def obtener_hoja_metas(sh):
    try:
        return sh.worksheet("Metas")
    except:
        hoja_m = sh.add_worksheet(title="Metas", rows="50", cols="2")
        hoja_m.append_row(["Nombre", "Monto_Objetivo"])
        hoja_m.append_row(["Proyecto Moto XR250", 3000000])
        hoja_m.append_row(["Ahorro / Interlagos F1", 1500000])
        return hoja_m

hoja_metas = obtener_hoja_metas(sh)

# 2. FUNCIONES PARA LEER Y GUARDAR EN LA NUBE
def cargar_datos():
    datos = hoja.get_all_records()
    if len(datos) > 0:
        df = pd.DataFrame(datos)
        df.columns = df.columns.str.strip() 
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        return df
    else:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Categoría", "Monto", "Descripción"])

def cargar_metas():
    datos = hoja_metas.get_all_records()
    if len(datos) > 0:
        df_m = pd.DataFrame(datos)
        df_m['Monto_Objetivo'] = pd.to_numeric(df_m['Monto_Objetivo'], errors='coerce')
        return df_m
    else:
        return pd.DataFrame(columns=["Nombre", "Monto_Objetivo"])

def guardar_registro(fecha, tipo, categoria, monto, descripcion):
    hoja.insert_row([str(fecha), tipo, categoria, monto, descripcion], index=2)

def guardar_meta(nombre, monto):
    hoja_metas.append_row([nombre, monto])

def borrar_ultimo_registro(df):
    datos = hoja.get_all_records()
    if len(datos) > 0:
        hoja.delete_rows(2)

df = cargar_datos()
df_metas = cargar_metas()

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

# --- OBTENCIÓN AUTOMÁTICA DEL DÓLAR BLUE ---
@st.cache_data(ttl=3600)
def obtener_dolar_blue():
    try:
        url = "https://dolarapi.com/v1/dolares/blue"
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        return float(datos["venta"])
    except:
        return 1200.0

dolar_hoy = obtener_dolar_blue()

cotizacion_usd = st.sidebar.number_input("Cotización Dólar Blue (ARS)", min_value=500.0, value=dolar_hoy, step=10.0)
st.sidebar.caption("🔄 Actualizado automáticamente via DolarApi")
st.sidebar.markdown("---")

# Formulario de carga de movimientos
with st.sidebar.form("formulario_movimientos", clear_on_submit=True):
    st.subheader("➕ Nuevo Registro")
    fecha = st.date_input("Fecha", datetime.today())
    tipo = st.selectbox("Tipo", ["Egreso", "Ingreso"])
    
    # [NUEVO] Sistema de Categorías Dinámicas y Personalizables
    if tipo == "Ingreso":
        cat_base = ["YPF (Sueldo/Bono)", "Negocio e Inversiones", "Otros Ingresos"]
    else:
        cat_base = [
            "Costos Fijos (Alquiler/Servicios)", 
            "Salidas y Joda", 
            "Compras Buenas (Valor/Bienestar)", 
            "Compras Malas (Impulso/Arrepentimiento)", 
            "Mantenimiento Moto / Nafta",
            "Suscripciones (Netflix/Gym)"
        ]
        # Inyectamos las metas guardadas como opciones automáticas de Egreso (Ahorro)
        for meta_nombre in df_metas["Nombre"].unique():
            if meta_nombre not in cat_base:
                cat_base.append(meta_nombre)
                
    # Leemos qué otras categorías ya existen en el historial para no perderlas
    cat_historial = list(df[df["Tipo"] == tipo]["Categoría"].dropna().unique()) if not df.empty else []
    cat_totales = sorted(list(set(cat_base + cat_historial))) + ["➕ Agregar Nueva Categoría..."]
    
    categoria_sel = st.selectbox("Categoría", cat_totales)
    
    # Si elige crear una, se habilita el text_input fuera del formulario o controlado por el flujo
    categoria_final = categoria_sel
    if categoria_sel == "➕ Agregar Nueva Categoría...":
        categoria_final = st.text_input("Nombre de la nueva categoría:")
        
    monto = st.number_input("Monto (ARS)", min_value=0.0, step=1000.0, format="%.2f")
    descripcion = st.text_input("Descripción breve")
    
    boton_guardar = st.form_submit_button("Guardar Movimiento")
    
    if boton_guardar and monto > 0 and categoria_final != "":
        guardar_registro(fecha, tipo, categoria_final, monto, descripcion)
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
tab_dashboard, tab_historial, tab_metas = st.tabs(["📈 Dashboard y Análisis", "📝 Historial de Movimientos", "🎯 Mis Metas e Inteligencia Predictiva"])

# --- PESTAÑA 1: DASHBOARD ---
with tab_dashboard:
    ingresos_totales = df_filtrado[df_filtrado["Tipo"] == "Ingreso"]["Monto"].sum() if not df_filtrado.empty else 0
    egresos_totales = df_filtrado[df_filtrado["Tipo"] == "Egreso"]["Monto"].sum() if not df_filtrado.empty else 0
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
        
        df_egresos = df_filtrado[df_filtrado["Tipo"] == "Egreso"]
        gasto_fijo = df_egresos[df_egresos["Categoría"].isin(cat_fijos)]["Monto"].sum()
        
        # Cualquier gasto asignado a las metas cuenta como ahorro activo
        gasto_ahorro = df_egresos[df_egresos["Categoría"].isin(df_metas["Nombre"].unique())]["Monto"].sum()
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

# --- PESTAÑA 3: METAS E INTELIGENCIA PREDICTIVA ---
with tab_metas:
    st.subheader("🎯 Objetivos Financieros Activos")
    
    # Formulario para añadir nuevas metas manualmente
    with st.expander("➕ Añadir Nueva Meta Personalizada"):
        with st.form("form_nueva_meta", clear_on_submit=True):
            nombre_m = st.text_input("Nombre del Objetivo (ej: Computadora nueva, Vacaciones)")
            monto_m = st.number_input("Monto Objetivo (ARS)", min_value=1000.0, step=50000.0)
            btn_meta = st.form_submit_button("Crear Meta")
            if btn_meta and nombre_m != "" and monto_m > 0:
                guardar_meta(nombre_m, monto_m)
                st.success(f"¡Meta '{nombre_m}' agregada! Reiniciando...")
                st.invalidate_resource(conectar_sheets)
                st.rerun()

    st.markdown("---")
    
    # Calcular cuántos meses de historial real tiene la base de datos para promediar
    if not df.empty:
        meses_historial = max(df['Fecha'].dt.to_period('M').nunique(), 1)
    else:
        meses_historial = 1

    # Desplegar cada meta cargada desde la nube
    if not df_metas.empty:
        for index, fila in df_metas.iterrows():
            meta_nombre = fila["Nombre"]
            objetivo_monto = fila["Monto_Objetivo"]
            
            # Sumar lo que se guardó bajo esa categoría en el historial
            total_acumulado = df[df["Categoría"] == meta_nombre]["Monto"].sum() if not df.empty else 0
            pct_progreso = min(total_acumulado / objetivo_monto, 1.0) if objetivo_monto > 0 else 0
            
            st.markdown(f"### 🚀 {meta_nombre}")
            
            col_bar, col_pred = st.columns([3, 2])
            
            with col_bar:
                st.progress(pct_progreso, text=f"${total_acumulado:,.0f} de ${objetivo_monto:,.0f} ({pct_progreso*100:.1f}%)")
            
            with col_pred:
                monto_faltante = objetivo_monto - total_acumulado
                promedio_mensual = total_acumulado / meses_historial
                
                if monto_faltante <= 0:
                    st.success("🎉 ¡Felicidades! Meta 100% alcanzada.")
                elif promedio_mensual > 0:
                    meses_restantes = monto_faltante / promedio_mensual
                    fecha_proyeccion = datetime.today() + timedelta(days=int(meses_restantes * 30.4))
                    st.info(f"🔮 **Predicción:** Al ritmo de ahorro actual (${promedio_mensual:,.0f}/mes), completás la meta en **{meses_restantes:.1f} meses** (Aprox. en **{fecha_proyeccion.strftime('%m/%Y')}**).")
                else:
                    st.warning("⚠️ Sin aportes este mes. Asigná un egreso a esta categoría para activar las predicciones en tiempo real.")
            st.markdown("---")
    else:
        st.info("No hay metas configuradas en tu base de datos.")
