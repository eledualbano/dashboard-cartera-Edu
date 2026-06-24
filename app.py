import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

st.set_page_config(page_title="Mi Cartera de Inversiones", layout="wide")

# --- CONFIGURACIÓN ---
SPREADSHEET_ID = "1-7fKak1B_R0_Udm83xrIwUzrwNPrQgHqcMflJlIhQA0"
GID_PRINCIPAL = "1816748277"
GID_HISTORIAL = "39842440" 

CSV_URL_ACTIVOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_PRINCIPAL}"
CSV_URL_HISTORIAL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_HISTORIAL}"

# Rangos de datos
FILA_INICIAL = 196 
FILA_FINAL = 217
RANGO_ON = range(236, 243)      # Filas 239 a 245 (ajustar si es necesario)
RANGO_CEDEAR = range(245, 259)  # Filas 248 a 261 (ajustar si es necesario)

def limpiar_num(valor):
    try:
        return float(str(valor).replace("$", "").replace(",", "").strip())
    except:
        return 0.0

@st.cache_data(ttl=60)
def cargar_datos():
    df_raw = pd.read_csv(CSV_URL_ACTIVOS, header=None)
    activos_data = []
    total = 0.0
    for i in range(FILA_INICIAL, FILA_FINAL + 1):
        ticker = str(df_raw.iloc[i, 1]).strip()
        valor = limpiar_num(df_raw.iloc[i, 2])
        nominales = limpiar_num(df_raw.iloc[i, 3])
        if ticker and ticker != 'nan' and valor > 0:
            activos_data.append({"Ticker": f"{ticker} ({ (valor/nominales) if nominales>0 else 0:,.2f})", "Valor": valor})
            total += valor
    return pd.DataFrame(activos_data), total

@st.cache_data(ttl=60)
def cargar_historial():
    df_hist = pd.read_csv(CSV_URL_HISTORIAL)
    df_hist.columns = df_hist.columns.str.strip().str.upper()
    df_hist['FECHA_DT'] = pd.to_datetime(df_hist['FECHA'], dayfirst=True, errors='coerce').dt.normalize()
    df_hist = df_hist.dropna(subset=['FECHA_DT', 'TOTAL']).sort_values("FECHA_DT")
    df_hist['FECHA_STR'] = df_hist['FECHA_DT'].dt.strftime('%d/%m/%Y')
    return df_hist

@st.cache_data(ttl=60)
def cargar_datos_torta():
    df_raw = pd.read_csv(CSV_URL_ACTIVOS, header=None)
    data = []
    # Procesar ONs
    for i in RANGO_ON:
        ticker = str(df_raw.iloc[i, 13]).strip()
        valor = limpiar_num(df_raw.iloc[i, 14])
        if ticker and ticker != 'nan' and valor > 0:
            data.append({"Instrumento": "ON", "Valor": valor})
    # Procesar CEDEARs
    for i in RANGO_CEDEAR:
        ticker = str(df_raw.iloc[i, 13]).strip()
        valor = limpiar_num(df_raw.iloc[i, 14])
        if ticker and ticker != 'nan' and valor > 0:
            data.append({"Instrumento": "CEDEAR", "Valor": valor})
    return pd.DataFrame(data)

# --- DASHBOARD ---
st.title("💼 Cartera de Inversiones")

df, total = cargar_datos()
df_torta = cargar_datos_torta()

col1, col2 = st.columns(2)
col1.metric("Valor Total", f"USD {total:,.0f}")
col2.metric("Cant. Activos", len(df))

# Gráficos
c1, c2 = st.columns(2)
with c1:
    st.subheader("📊 Distribución por Activo")
    st.plotly_chart(px.bar(df.sort_values("Valor", ascending=False), x="Ticker", y="Valor", text_auto='.0f'), use_container_width=True)
with c2:
    st.subheader("🥧 Composición (CEDEAR/ON)")
    if not df_torta.empty:
        st.plotly_chart(px.pie(df_torta, values="Valor", names="Instrumento", hole=0.3), use_container_width=True)

st.subheader("📈 Evolución Histórica (Diaria)")
df_hist = cargar_historial()
if not df_hist.empty:
    st.line_chart(df_hist.set_index("FECHA_STR")[["TOTAL"]])

st.subheader("Detalle de Activos")
st.table(df.assign(Valor=df["Valor"].apply(lambda x: f"{x:,.2f}")))
