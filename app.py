import pandas as pd
import streamlit as st
import io

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="📊 Indicadores INE por Municipio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------- LOAD DATASETS --------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_parquet("structured_population.parquet")
        df.columns = df.columns.astype(str)
        df_censo = pd.read_parquet("structured_censo.parquet")
        df_hog_2011 = pd.read_parquet("structured_censo2011_hogares.parquet")
        df_hog_2021 = pd.read_parquet("structured_censo2021_hogares.parquet")
        df_censo2011 = pd.read_parquet("structured_censo2011_viviendas.parquet")
        return df, df_censo, df_hog_2011, df_hog_2021, df_censo2011
    except Exception as e:
        st.error(f"❌ No se pudieron cargar los archivos Parquet: {e}")
        st.stop()

# Load data
df, df_censo, df_hog_2011, df_hog_2021, df_censo2011 = load_data()

# Constants
YEARS = ["2024", "2023", "2022", "2021"]
age_65_plus = ["65_69", "70_74", "75_79", "80_84", "85_89", "90_94", "95_99", "100"]
age_85_plus = ["85_89", "90_94", "95_99", "100"]
ages_0_14 = ["0_4", "5_9", "10_14"]
ages_15_64 = ["15_19", "20_24", "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59", "60_64"]

# -------------------- MAIN APP --------------------
st.title("📊 Indicadores INE por Municipio")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🏨️ Selección de Municipio")
    municipalities = sorted(df["municipio"].dropna().unique(), key=str.lower)
    search_term = st.text_input("🔍 Buscar municipio:", placeholder="Escribe para buscar un municipio...")
    
    if search_term:
        filtered_municipalities = [m for m in municipalities if search_term.lower() in m.lower()]
        if filtered_municipalities:
            selected_muni = st.selectbox("Municipios encontrados:", filtered_municipalities, index=None)
        else:
            st.warning("❌ No se encontraron municipios que coincidan con tu búsqueda.")
            selected_muni = None
    else:
        selected_muni = st.selectbox("O selecciona directamente:", municipalities, index=None)

with col2:
    if selected_muni:
        st.markdown("### ℹ️ Información")
        st.info(f"**Municipio seleccionado:**\n{selected_muni}")
        try:
            total_pop_2024 = df[df["municipio"] == selected_muni]["total_total_total_2024"].values[0]
            st.metric("Población Total 2024", f"{total_pop_2024:,}" if total_pop_2024 else "No disponible")
        except:
            pass

if selected_muni:
    st.markdown("---")
    pop_df = df[df["municipio"] == selected_muni]
    if pop_df.empty:
        st.error("❌ No se encontraron datos para el municipio seleccionado.")
        st.stop()

    muni_code = selected_muni.split()[0]
    censo_df = df_censo[df_censo["Municipio de residencia"].str.startswith(muni_code)]

    # Vivienda/hogar histórico
    hog_2011 = df_hog_2011[df_hog_2011["municipio"].str.contains(selected_muni, case=False, na=False)]
    hog_2021 = df_hog_2021[df_hog_2021["municipio"].str.contains(selected_muni, case=False, na=False)]
    viv_2011 = df_censo2011[df_censo2011["Municipio de residencia"].str.contains(selected_muni, case=False, na=False)]

    try:
        n_hog_2011 = hog_2011["nHogares"].values[0]
        n_hog_2021 = hog_2021["nHogares"].values[0]
        var_hogares_pct = round((n_hog_2021 - n_hog_2011) / n_hog_2011 * 100, 2)
    except:
        var_hogares_pct = None

    try:
        n_viv_2011 = viv_2011["viviendasTotal"].values[0]
        n_viv_2021 = censo_df["viviendasT"].values[0]
        crecimiento_viviendas_pct = round((n_viv_2021 - n_viv_2011) / n_viv_2011 * 100, 2)
    except:
        crecimiento_viviendas_pct = None

    try:
        n_viv_vacias_2011 = viv_2011["viviendasVacias"].values[0]
        viv_vacia_pct_2011 = round(n_viv_vacias_2011 / n_viv_2011 * 100, 2)
    except:
        viv_vacia_pct_2011 = None

    results = []
    for year in YEARS:
        total = pop_df.get(f"total_total_total_{year}", pd.Series([0])).values[0]
        over_65 = pop_df[[f"total_{age}_total_{year}" for age in age_65_plus if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
        over_85 = pop_df[[f"total_{age}_total_{year}" for age in age_85_plus if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
        foreign = pop_df.get(f"total_total_EX_{year}", pd.Series([0])).values[0]
        pop_0_14 = pop_df[[f"total_{age}_total_{year}" for age in ages_0_14 if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
        pop_15_64 = pop_df[[f"total_{age}_total_{year}" for age in ages_15_64 if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]

        row = {
            "Año": year,
            "D.22.a. Envejecimiento (%)": round(over_65 / total * 100, 2) if total else None,
            "D.22.b. Senectud (%)": round(over_85 / over_65 * 100, 2) if over_65 else None,
            "Población extranjera (%)": round(foreign / total * 100, 2) if total else None,
            "D.24.a. Dependencia total (%)": round((pop_0_14 + over_65) / pop_15_64 * 100, 2) if pop_15_64 else None,
            "D.24.b. Dependencia infantil (%)": round(pop_0_14 / pop_15_64 * 100, 2) if pop_15_64 else None,
            "D.24.c. Dependencia mayores (%)": round(over_65 / pop_15_64 * 100, 2) if pop_15_64 else None,
            "%Vivienda secundaria": None,
            "D.25 Viviendas por persona": None,
            "VARIACIÓN HOGARES 2011-2021 (%)": var_hogares_pct if year == "2021" else None,
            "CRECIMIENTO PARQUE VIVIENDAS 2011-2021 (%)": crecimiento_viviendas_pct if year == "2021" else None,
            "VIVIENDA VACÍA 2011 (%)": viv_vacia_pct_2011 if year == "2021" else None
        }

        if year == "2021":
            try:
                v_total = censo_df["viviendasT"].values[0]
                v_nop = censo_df["viviendasNoP"].values[0]
                pop_2021 = pop_df["total_total_total_2021"].values[0]
                row["%Vivienda secundaria"] = round((v_nop / v_total) * 100, 2)
                row["D.25 Viviendas por persona"] = round((v_total / pop_2021) * 1000, 4)
            except:
                pass

        results.append(row)

    results_df = pd.DataFrame(results)
    st.markdown(f"### 📈 Indicadores para **{selected_muni}**")
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        csv = results_df.to_csv(index=False)
        st.download_button("📥 Descargar CSV", csv, f"indicadores_{selected_muni.replace(' ', '_')}.csv", "text/csv")
    with col2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            results_df.to_excel(writer, index=False, sheet_name="Indicadores")
        st.download_button("📊 Descargar Excel", buffer.getvalue(), f"indicadores_{selected_muni.replace(' ', '_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.markdown("---")
    st.info("👆 **Instrucciones:**\n1. Usa el cuadro de búsqueda para encontrar un municipio\n2. O selecciona directamente de la lista desplegable\n3. Los indicadores se mostrarán automáticamente")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Municipios", len(municipalities))
    with col2:
        st.metric("Años de Datos", len(YEARS))
    with col3:
        st.metric("Indicadores", "12")

st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        📊 Aplicación de Indicadores INE por Municipio<br>
        Datos del Instituto Nacional de Estadística (INE)
    </div>
    """, unsafe_allow_html=True)
