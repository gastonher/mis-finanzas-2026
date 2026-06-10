import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Mi Ecosistema Financiero", page_icon="📊", layout="wide")

# Archivo de por vida
ARCHIVO_DATOS = "mis_finanzas_2026.csv"

# 2. FUNCIONES PARA GUARDAR Y LEER DATOS
def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    else:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Categoría", "Monto", "Descripción"])

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

df = cargar_datos()

# 3. BARRA LATERAL (PANEL DE CARGA)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/YPF_logo.svg/1200px-YPF_logo.svg.png", width=100)
st.sidebar.title("Panel de Carga")

# Conversor Bimonetario
cotizacion_usd = st.sidebar.number_input("Cotización Dólar (ARS/USD)", min_value=500.0, value=1200.0, step=10.0)
st.sidebar.markdown("---")

# Formulario de carga de movimientos
with st.sidebar.form("formulario_movimientos", clear_on_submit=True):
    st.subheader("➕ Nuevo Registro")
    fecha = st.date_input("Fecha", datetime.today())
    tipo = st.selectbox("Tipo", ["Egreso", "Ingreso"])
    
    if tipo == "Ingreso":
        categoria = st.selectbox("Categoría", ["YPF (Sueldo/Bono)", "Negocio e Inversiones", "Otros Ingresos"])
    else:
        # AQUÍ ESTÁN TUS NUEVAS CATEGORÍAS OPTIMIZADAS
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
    descripcion = st.text_input("Descripción (Ej: Cena con amigos, Curso, Camisa)")
    
    boton_guardar = st.form_submit_button("Guardar Movimiento")
    
    if boton_guardar and monto > 0:
        nuevo_registro = pd.DataFrame([{
            "Fecha": fecha, "Tipo": tipo, "Categoría": categoria, 
            "Monto": monto, "Descripción": descripcion
        }])
        df = pd.concat([df, nuevo_registro], ignore_index=True)
        guardar_datos(df)
        st.success("¡Guardado correctamente!")
        st.rerun()

# 4. PANTALLA PRINCIPAL (DASHBOARD)
st.title("📊 Ecosistema Financiero Personal")
st.markdown("Gestión patrimonial inteligente para YPF, Negocios y Objetivos Estratégicos.")

# Cálculos automáticos
ingresos_totales = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
egresos_totales = df[df["Tipo"] == "Egreso"]["Monto"].sum()
saldo_actual = ingresos_totales - egresos_totales
saldo_usd = saldo_actual / cotizacion_usd if cotizacion_usd > 0 else 0

# Tarjetas de Resumen
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ingresos Totales", f"${ingresos_totales:,.0f}")
col2.metric("Egresos Totales", f"${egresos_totales:,.0f}")
col3.metric("Saldo Disponible (ARS)", f"${saldo_actual:,.0f}")
col4.metric("Saldo en USD", f"US$ {saldo_usd:,.0f}")

st.markdown("---")

# 5. GRÁFICOS INTERACTIVOS
if not df.empty and egresos_totales > 0:
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("Distribución de Egresos")
        df_egresos = df[df["Tipo"] == "Egreso"]
        fig_torta = px.pie(df_egresos, values="Monto", names="Categoría", hole=0.4, 
                           color_discrete_sequence=px.colors.sequential.Bluyl) # Cambié a una paleta azul/amarilla elegante
        st.plotly_chart(fig_torta, use_container_width=True)
        
    with col_graf2:
        st.subheader("Balance por Categoría")
        df_agrupado = df.groupby(["Categoría", "Tipo"])["Monto"].sum().reset_index()
        fig_barras = px.bar(df_agrupado, x="Categoría", y="Monto", color="Tipo", barmode="group",
                            color_discrete_map={"Ingreso": "#2a9d8f", "Egreso": "#e63946"})
        st.plotly_chart(fig_barras, use_container_width=True)

# 6. TABLA DE HISTORIAL
st.markdown("---")
st.subheader("📝 Historial de Movimientos")
df_mostrar = df.sort_values(by="Fecha", ascending=False).reset_index(drop=True)
st.dataframe(df_mostrar, use_container_width=True)
