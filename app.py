import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Inversiones", layout="wide")

# --- CONFIGURACIÓN DE TU PLANILLA REAL ---
SPREADSHEET_ID = "1-7fKak1B_R0_Udm83xrIwUzrwNPrQgHqcMflJlIhQA0"
GID_PRINCIPAL = "1816748277"  # Pestaña "2026"

# 🎯 Filtramos estrictamente el rango de la tabla final que me indicaste
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_PRINCIPAL}&range=B193:D214"

# --- CONFIGURACIÓN DE TU PESTAÑA HISTORIAL ---
GID_HISTORIAL = 39842440 
CSV_HISTORIAL_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_HISTORIAL}"

# Tickers oficiales para la separación de pestañas
ON_TICKERS = ["YM34D", "RUCDD", "DNC5D", "DNC7D", "TLCPD", "IRCPD", "TLCTD", "MR39D", "RUCAD"]
CEDEAR_TICKERS = [
    "MELI", "B", "PBR", "JNJ", "WMT", "PAMP", "PFE", "SPY ETF", 
    "BRKB", "META", "GOOGL", "MSFT", "NU", "NVDA", "VIST", "GOLD"
]

def limpiar_monto_puro(valor):
    if pd.isna(valor):
        return 0.0
    val_str = str(valor).strip().replace("$", "").replace("U$S", "").replace(" ", "")
    if val_str == "-" or not val_str or val_str.lower() == "nan":
        return 0.0
    try:
        if "," in val_str and "." in val_str:
            if val_str.find(",") < val_str.find("."):
                val_str = val_str.replace(",", "")
            else:
                val_str = val_str.replace(".", "").replace(",", ".")
        elif "," in val_str:
            partes = val_str.split(",")
            if len(partes) == 2 and len(partes[1]) == 2:
                val_str = val_str.replace(",", ".")
            else:
                val_str = val_str.replace(",", "")
        return float(val_str)
    except ValueError:
        return 0.0

@st.cache_data(ttl=5)
def cargar_datos_desde_sheets():
    try:
        # Cargamos asignando los nombres exactos a las 3 columnas del rango
        df = pd.read_csv(CSV_URL, header=None, names=["TICKER", "VALOR_TOTAL_USD", "NOMINALES"], engine='python')
        
        portfolio = {
            "total_usd": 0.0,
            "instrumentos": {"Obligaciones Negociables": 0.0, "CEDEARs": 0.0},
            "activos": {}
        }

        for _, row in df.iterrows():
            ticker_raw = row["TICKER"]
            if pd.isna(ticker_raw):
                continue
                
            ticker = str(ticker_raw).strip().upper()
            
            es_on = ticker in ON_TICKERS
            es_cedear = ticker in CEDEAR_TICKERS
            if not (es_on or es_cedear):
                continue

            # Lectura directa de los valores declarados de tus celdas C y D
            valor_final_usd = limpiar_monto_puro(row["VALOR_TOTAL_USD"])
            nominales = limpiar_monto_puro(row["NOMINALES"])
            
            if valor_final_usd <= 0:
                continue

            tipo = "Obligaciones Negociables" if es_on else "CEDEARs"
            precio_unitario = (valor_final_usd / nominales) if nominales > 0 else 0.0

            portfolio["activos"][ticker] = {
                "precio_unitario": round(precio_unitario, 2),
                "total_posicion_usd": round(valor_final_usd, 2)
            }
            portfolio["instrumentos"][tipo] += valor_final_usd
            portfolio["total_usd"] += valor_final_usd

        portfolio["total_usd"] = round(portfolio["total_usd"], 2)
        for inst in portfolio["instrumentos"]:
            portfolio["instrumentos"][inst] = round(portfolio["instrumentos"][inst], 2)
            
        return portfolio
    except Exception as e:
        return None

@st.cache_data(ttl=5)
def cargar_historial():
    try:
        df_hist = pd.read_csv(CSV_HISTORIAL_URL, engine='python')
        if df_hist.empty:
            return None, None, None
            
        df_hist.columns = [c.strip().upper() for c in df_hist.columns]
        col_fecha = [c for c in df_hist.columns if "FECHA" in c][0]
        col_total = [c for c in df_hist.columns if "TOTAL" in c][0]
        
        df_hist = df_hist[[col_fecha, col_total]].dropna()
        df_hist[col_total] = df_hist[col_total].apply(limpiar_monto_puro)
        df_hist[col_fecha] = pd.to_datetime(df_hist[col_fecha], dayfirst=True, errors='coerce')
        df_hist = df_hist.dropna().sort_values(by=col_fecha)
        return df_hist, col_fecha, col_total
    except Exception as e:
        return None, None, None

# --- RENDERIZADO DEL DASHBOARD ---
portfolio = cargar_datos_desde_sheets()
df_historial, col_f, col_t = cargar_historial()

st.title("💼 Mi Cartera de Inversiones Automatizada")
# Corrección de sintaxis limpia para evitar incompatibilidades de versión
st.markdown("_Sincronización exacta apuntando al rango de control B193:D214_")
st.markdown("---")

if portfolio and portfolio["activos"]:
    tab_gral, tab_ons, tab_cedears = st.tabs(["📊 Resumen General", "📜 Análisis de ONs", "🍎 Análisis de CEDEARs"])
    total_general = portfolio["total_usd"] if portfolio["total_usd"] > 0 else 1.0
    
    datos_activos = []
    datos_ons = []
    datos_cedears = []

    for tk, info in portfolio["activos"].items():
        valor_usd = info["total_posicion_usd"]
        porcentaje_global = (valor_usd / total_general) * 100
        item = {"Ticker": tk, "Valor USD": valor_usd, "% del Total": round(porcentaje_global, 2), "Precio Ref": info.get("precio_unitario", 0.0)}
        datos_activos.append(item)
        if tk in ON_TICKERS: datos_ons.append(item)
        elif tk in CEDEAR_TICKERS: datos_cedears.append(item)

    df_activos_todos = pd.DataFrame(datos_activos)

    with tab_gral:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="Valor Total de la Cartera", value=f"USD {portfolio['total_usd']:,.2f}")
        with col2:
            top_asset = max(portfolio["activos"], key=lambda k: portfolio["activos"][k]["total_posicion_usd"])
            st.metric(label="Activo de Mayor Peso", value=f"{top_asset}", delta=f"USD {portfolio['activos'][top_asset]['total_posicion_usd']:,.2f}")
        with col3: st.metric(label="Cantidad de Activos en Cartera", value=len(portfolio["activos"]))

        st.markdown("---")
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Composición por Instrumento")
            df_inst = pd.DataFrame(list(portfolio["instrumentos"].items()), columns=["Instrumento", "Valor USD"])
            fig_pie = px.pie(df_inst, values="Valor USD", names="Instrumento", color_discrete_sequence=["#3b82f6", "#ef4444"], hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_graf2:
            st.subheader("Distribución Porcentual")
            df_bar_pct = df_activos_todos.sort_values(by="% del Total", ascending=False)
            fig_bar = px.bar(df_bar_pct, x="Ticker", y="% del Total", text="% del Total", color_discrete_sequence=["#6366f1"])
            fig_bar.update_traces(texttemplate='%{text}%', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

        if df_historial is not None and not df_historial.empty:
            st.markdown("---")
            st.subheader("📈 Evolución Histórica")
            fig_evolucion = px.line(df_historial, x=col_f, y=col_t, markers=True, color_discrete_sequence=["#10b981"])
            st.plotly_chart(fig_evolucion, use_container_width=True)

        st.markdown("---")
        st.subheader("📌 Desglose Detallado por Activo")
        activos_ordenados = sorted(datos_activos, key=lambda x: x["Valor USD"], reverse=True)
        cols_activos = st.columns(3)
        for i, activo in enumerate(activos_ordenados):
            with cols_activos[i % 3]:
                st.metric(label=f"{activo['Ticker']} ({activo['% del Total']}% del total)", value=f"USD {activo['Valor USD']:,.2f}")

    with tab_ons:
        if datos_ons:
            df_ons = pd.DataFrame(datos_ons)
            total_ons = df_ons["Valor USD"].sum()
            df_ons["% de la Subcartera"] = round((df_ons["Valor USD"] / total_ons) * 100, 2)
            c1, c2 = st.columns(2)
            with c1:
                st.metric(label="Total Invertido en ONs", value=f"USD {total_ons:,.2f}")
                st.dataframe(df_ons[["Ticker", "Valor USD", "% del Total", "% de la Subcartera"]].sort_values(by="Valor USD", ascending=False), hide_index=True, use_container_width=True)
            with c2: st.plotly_chart(px.pie(df_ons, values="Valor USD", names="Ticker", hole=0.3), use_container_width=True)

    with tab_cedears:
        if datos_cedears:
            df_cedears = pd.DataFrame(datos_cedears)
            total_cedears = df_cedears["Valor USD"].sum()
            df_cedears["% de la Subcartera"] = round((df_cedears["Valor USD"] / total_cedears) * 100, 2)
            c1, c2 = st.columns(2)
            with c1:
                st.metric(label="Total Invertido en CEDEARs", value=f"USD {total_cedears:,.2f}")
                st.dataframe(df_cedears[["Ticker", "Valor USD", "% del Total", "% de la Subcartera"]].sort_values(by="Valor USD", ascending=False), hide_index=True, use_container_width=True)
            with c2: st.plotly_chart(px.pie(df_cedears, values="Valor USD", names="Ticker", hole=0.3), use_container_width=True)
else:
    st.warning("Verificando consistencia de datos en el rango seleccionado...")
