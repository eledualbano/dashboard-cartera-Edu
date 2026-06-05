import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Inversiones", layout="wide")

# --- CONFIGURACIÓN DE TU PLANILLA REAL (TOTALMENTE DINÁMICA) ---
SPREADSHEET_ID = "1-7fKak1B_R0_Udm83xrIwUzrwNPrQgHqcMflJlIhQA0"
GID_PRINCIPAL = "1816748277"  # Pestaña "2026"

# 🔍 LEEMOS DESDE LA FILA 1: Abarcamos toda la hoja para no perder ningún activo de arriba
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_PRINCIPAL}&range=B1:D350"

# --- GID DE TU PESTAÑA HISTORIAL ---
GID_HISTORIAL = 39842440 
CSV_HISTORIAL_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_HISTORIAL}"

ON_TICKERS = ["MR39D", "IRCPD", "TLCPD", "YM34D", "DNC5D", "DNC7D", "RUCAD", "RUCDD", "TLCTD"]
CEDEAR_TICKERS = [
    "VIST", "MSFT", "WMT", "GOLD", "PBR", "SPY ETF", "NU", "META", 
    "GOOGL", "MELI", "NVDA", "BRKB", "PFE", "JNJ", "B"
]

def limpiar_numero(valor):
    if pd.isna(valor):
        return 0.0
    val_str = str(valor).strip().replace("$", "").replace(" ", "").replace("U$S", "")
    if val_str == "-" or not val_str:
        return 0.0
    try:
        if "," in val_str and "." in val_str:
            if val_str.find(".") < val_str.find(","):
                val_str = val_str.replace(".", "").replace(",", ".")
            else:
                val_str = val_str.replace(",", "")
        elif "," in val_str:
            val_str = val_str.replace(",", ".")
        return float(val_str)
    except ValueError:
        return 0.0

@st.cache_data(ttl=60)
def cargar_datos_desde_sheets():
    try:
        # Forzamos header=None porque leemos desde la fila 1 y no queremos usar textos de arriba como títulos
        df = pd.read_csv(CSV_URL, header=None, names=["TICKER", "VALOR_USD", "NOMINALES"], engine='python')
        
        portfolio = {
            "total_usd": 0.0,
            "instrumentos": {"Obligaciones Negociables": 0.0, "CEDEARs": 0.0, "Merval": 0.0},
            "activos": {}
        }

        for _, row in df.iterrows():
            ticker_raw = row["TICKER"]
            valor_raw = row["VALOR_USD"]
            nominales_raw = row["NOMINALES"]
            
            # Si la celda está vacía o no es texto válido, saltamos de fila
            if pd.isna(ticker_raw):
                continue
                
            ticker = str(ticker_raw).strip().upper()
            
            # 🛑 FRENO DINÁMICO: Al llegar al "TOTAL GENERAL" dejamos de leer filas hacia abajo
            if "TOTAL GENERAL" in ticker or "TOTAL APORTADO" in ticker:
                break
                
            valor_posicion_usd = limpiar_numero(valor_raw)
            nominales = limpiar_numero(nominales_raw)
            
            # 🧠 FILTRO INTELIGENTE: Si tiene texto (ej: "Ticker", "Cant") pero los números dan 0,
            # significa que es un título de arriba o una fila vacía de la planilla. La ignoramos.
            if valor_posicion_usd <= 0 or nominales <= 0:
                continue

            if ticker in ON_TICKERS:
                tipo = "Obligaciones Negociables"
            elif ticker in CEDEAR_TICKERS:
                tipo = "CEDEARs"
            else:
                tipo = "Merval"

            precio_ref = valor_posicion_usd / nominales

            portfolio["activos"][ticker] = {
                "precio_unitario": round(precio_ref, 2),
                "total_posicion_usd": round(valor_posicion_usd, 2)
            }
            portfolio["instrumentos"][tipo] += valor_posicion_usd
            portfolio["total_usd"] += valor_posicion_usd

        portfolio["total_usd"] = round(portfolio["total_usd"], 2)
        for inst in portfolio["instrumentos"]:
            portfolio["instrumentos"][inst] = round(portfolio["instrumentos"][inst], 2)
            
        return portfolio
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

@st.cache_data(ttl=60)
def cargar_historial():
    try:
        df_hist = pd.read_csv(CSV_HISTORIAL_URL, engine='python')
        if df_hist.empty:
            return None, None, None
            
        df_hist.columns = [c.strip().upper() for c in df_hist.columns]
        
        col_fecha = [c for c in df_hist.columns if "FECHA" in c][0]
        col_total = [c for c in df_hist.columns if "TOTAL" in c][0]
        
        df_hist = df_hist[[col_fecha, col_total]].dropna()
        df_hist[col_total] = df_hist[col_total].apply(limpiar_numero)
        
        # 📅 INDICA DÍA PRIMERO (dd/mm/yyyy) para que lea bien el historial guardado por la macro
        df_hist[col_fecha] = pd.to_datetime(df_hist[col_fecha], dayfirst=True, errors='coerce')
        
        df_hist = df_hist.dropna().sort_values(by=col_fecha)
        return df_hist, col_fecha, col_total
    except Exception as e:
        return None, None, None

# --- CARGA DE DATOS ---
portfolio = cargar_datos_desde_sheets()
df_historial, col_f, col_t = cargar_historial()

st.title("💼 Mi Cartera de Inversiones Automatizada")
st.caption("Datos sincronizados en tiempo real desde tu Google Sheets")
st.markdown("---")

if portfolio:
    tab_gral, tab_ons, tab_cedears = st.tabs([
        "📊 Resumen General", 
        "📜 Análisis de ONs", 
        "🍎 Análisis de CEDEARs"
    ])

    total_general = portfolio["total_usd"] if portfolio["total_usd"] > 0 else 1.0
    datos_activos = []
    datos_ons = []
    datos_cedears = []

    for tk, info in portfolio["activos"].items():
        valor_usd = info["total_posicion_usd"]
        porcentaje_global = (valor_usd / total_general) * 100
        
        item = {
            "Ticker": tk, 
            "Valor USD": valor_usd, 
            "% del Total": round(porcentaje_global, 2),
            "Precio Ref": info.get("precio_unitario", 0.0)
        }
        datos_activos.append(item)
        
        if tk in ON_TICKERS:
            datos_ons.append(item)
        elif tk in CEDEAR_TICKERS:
            datos_cedears.append(item)

    df_activos_todos = pd.DataFrame(datos_activos)

    # ==================== PESTAÑA 1: RESUMEN GENERAL ====================
    with tab_gral:
        if not portfolio["activos"]:
            st.info("Aún no tienes activos registrados en el rango mapeado de la planilla.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Valor Total de la Cartera", value=f"USD {portfolio['total_usd']:,.2f}")
            with col2:
                top_asset = max(portfolio["activos"], key=lambda k: portfolio["activos"][k]["total_posicion_usd"])
                st.metric(
                    label="Activo de Mayor Peso", 
                    value=f"{top_asset}", 
                    delta=f"USD {portfolio['activos'][top_asset]['total_posicion_usd']:,.2f}"
                )
            with col3:
                st.metric(label="Cantidad de Activos", value=len(portfolio["activos"]))

            st.markdown("---")

            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.subheader("Composición por Instrumento")
                df_inst = pd.DataFrame(list(portfolio["instrumentos"].items()), columns=["Instrumento", "Valor USD"])
                df_inst = df_inst[df_inst["Valor USD"] > 0]
                fig_pie = px.pie(df_inst, values="Valor USD", names="Instrumento", 
                                 color_discrete_sequence=["#3b82f6", "#10b981", "#8b5cf6"], hole=0.4)
                fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_graf2:
                st.subheader("Distribución Porcentual sobre el Total General")
                df_bar_pct = df_activos_todos.sort_values(by="% del Total", ascending=False)
                fig_bar = px.bar(df_bar_pct, x="Ticker", y="% del Total", text="% del Total", color_discrete_sequence=["#6366f1"])
                fig_bar.update_traces(texttemplate='%{text}%', textposition='outside')
                fig_bar.update_layout(yaxis=dict(ticksuffix="%"), margin=dict(t=30, b=20, l=20, r=20))
                st.plotly_chart(fig_bar, use_container_width=True)

            # 📉 --- GRÁFICO DE EVOLUCIÓN HISTÓRICA ---
            if df_historial is not None and not df_historial.empty:
                st.markdown("---")
                st.subheader("📈 Evolución Histórica de la Cartera")
                fig_evolucion = px.line(
                    df_historial, 
                    x=col_f, 
                    y=col_t, 
                    markers=True,
                    color_discrete_sequence=["#10b981"]
                )
                fig_evolucion.update_layout(
                    xaxis_title="Fecha",
                    yaxis_title="Monto Cartera (USD)",
                    hovermode="x unified",
                    template="plotly_dark"
                )
                fig_evolucion.update_xaxes(tickformat="%d/%m/%Y")
                st.plotly_chart(fig_evolucion, use_container_width=True)
            else:
                st.markdown("---")
                st.info("📈 Cuando la pestaña de Historial empiece a acumular registros diarios running la macro, acá se dibujará tu gráfico de evolución.")

            st.markdown("---")
            st.subheader("📌 Desglose Detallado por Activo")
            
            activos_ordenados = sorted(datos_activos, key=lambda x: x["Valor USD"], reverse=True)
            cols_activos = st.columns(3)
            for i, activo in enumerate(activos_ordenados):
                with cols_activos[i % 3]:
                    precio = activo["Precio Ref"]
                    sub_label = f"{activo['Ticker']} (Cotización Implícita: USD {precio:,.2f}) — {activo['% del Total']}% del total" if precio > 0 else f"{activo['Ticker']} — {activo['% del Total']}% del total"
                    st.metric(label=sub_label, value=f"USD {activo['Valor USD']:,.2f}")

    # ==================== PESTAÑA 2: ONs ====================
    with tab_ons:
        st.subheader("📜 Concentración Interna de Obligaciones Negociables")
        if not datos_ons:
            st.info("No posees Obligaciones Negociables en el rango leído.")
        else:
            df_ons = pd.DataFrame(datos_ons)
            total_ons = df_ons["Valor USD"].sum()
            df_ons["% de la Subcartera"] = round((df_ons["Valor USD"] / total_ons) * 100, 2)
            
            col_on1, col_on2 = st.columns([1, 1])
            with col_on1:
                st.metric(label="Total Invertido en ONs", value=f"USD {total_ons:,.2f}")
                st.dataframe(df_ons[["Ticker", "Valor USD", "% del Total", "% de la Subcartera"]].sort_values(by="Valor USD", ascending=False), hide_index=True, use_container_width=True)
            with col_on2:
                fig_pie_ons = px.pie(df_ons, values="Valor USD", names="Ticker", hole=0.3, color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig_pie_ons, use_container_width=True)

    # ==================== PESTAÑA 3: CEDEARS ====================
    with tab_cedears:
        st.subheader("🍎 Concentración Interna de CEDEARs")
        if not datos_cedears:
            st.info("No posees CEDEARs en el rango leído.")
        else:
            df_cedears = pd.DataFrame(datos_cedears)
            total_cedears = df_cedears["Valor USD"].sum()
            df_cedears["% de la Subcartera"] = round((df_cedears["Valor USD"] / total_cedears) * 100, 2)
            
            col_ced1, col_ced2 = st.columns([1, 1])
            with col_ced1:
                st.metric(label="Total Invertido en CEDEARs", value=f"USD {total_cedears:,.2f}")
                st.dataframe(df_cedears[["Ticker", "Valor USD", "% del Total", "% de la Subcartera"]].sort_values(by="Valor USD", ascending=False), hide_index=True, use_container_width=True)
            with col_ced2:
                fig_pie_ced = px.pie(df_cedears, values="Valor USD", names="Ticker", hole=0.3, color_discrete_sequence=px.colors.sequential.Reds_r)
                st.plotly_chart(fig_pie_ced, use_container_width=True)
