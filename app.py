import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

st.set_page_config(page_title="Mi Cartera de Inversiones", layout="wide")

# --- CONFIGURACIÓN ---
SPREADSHEET_ID = "1-7fKak1B_R0_Udm83xrIwUzrwNPrQgHqcMflJlIhQA0"
GID_PRINCIPAL = "1816748277"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_PRINCIPAL}"
HISTORIAL_FILE = "historial_cartera.csv"

# Rango fijo: Filas 194-216 (índices 193-215 en Python)
FILA_INICIAL = 193 
FILA_FINAL = 215

def limpiar_num(valor):
    try:
        if isinstance(valor, (int, float)): return float(valor)
        return float(str(valor).replace("$", "").replace(",", "").strip())
    except:
        return 0.0

@st.cache_data(ttl=60)
def cargar_datos():
    df_raw = pd.read_csv(CSV_URL, header=None)
    activos_data = []
    total = 0.0
    
    # Procesamiento por rango fijo
    for i in range(FILA_INICIAL, FILA_FINAL + 1):
        ticker = str(df_raw.iloc[i, 1]).strip()
        valor_total = limpiar_num(df_raw.iloc[i, 2])
        nominales = limpiar_num(df_raw.iloc[i, 3])
        
        if ticker and ticker.lower() != 'nan' and valor_total > 0:
            val_unitario = valor_total / nominales if nominales > 0 else 0
            activos_data.append({
                "Ticker": f"{ticker} ({val_unitario:,.2f})",
                "Valor": valor_total
            })
            total += valor_total
            
    df = pd.DataFrame(activos_data)
    
    # Manejo de Histórico
    fecha = datetime.datetime.now().strftime("%Y-%m-%d")
    df_hist_nuevo = pd.DataFrame({"Fecha": [fecha], "Total": [total]})
    if os.path.exists(HISTORIAL_FILE):
        hist = pd.read_csv(HISTORIAL_FILE)
        hist = pd.concat([hist[hist["Fecha"] != fecha], df_hist_nuevo])
        hist.to_csv(HISTORIAL_FILE, index=False)
    else:
        df_hist_nuevo.to_csv(HISTORIAL_FILE, index=False)
        
    return df, total

# --- DASHBOARD ---
df, total = cargar_datos()
df = df.sort_values("Valor", ascending=False)

st.title("💼 Cartera de Inversiones")

# Métricas (Total sin decimales)
col1, col2 = st.columns(2)
col1.metric("Valor Total", f"USD {total:,.0f}")
col2.metric("Cant. Activos", len(df))

# Gráfico de barras
st.subheader("📊 Distribución por Activo")
fig = px.bar(df, x="Ticker", y="Valor", text_auto='.0f')
st.plotly_chart(fig, use_container_width=True)

# Tendencia
st.subheader("📈 Evolución Histórica")
hist = pd.read_csv(HISTORIAL_FILE)
st.line_chart(hist.set_index("Fecha"))

# Tabla de detalle (Valor con dos decimales)
st.subheader("Detalle de Activos")
df_display = df.copy()
df_display["Valor"] = df_display["Valor"].apply(lambda x: f"{x:,.2f}")
st.table(df_display)
else:
    st.warning("Verificando consistencia de datos en el rango seleccionado...")
