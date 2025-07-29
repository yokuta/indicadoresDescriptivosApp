import pandas as pd
import streamlit as st
import io
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import zipfile
import tempfile
import os
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="📊 Indicadores INE por Municipio",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------- GEOSPATIAL FUNCTIONS --------------------
def process_shapefile(uploaded_file):
    """Process uploaded shapefile (zip) and return GeoDataFrame"""
    try:
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the zip file
            with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the .shp file
            shp_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.shp'):
                    shp_file = os.path.join(temp_dir, file)
                    break
            
            if shp_file is None:
                st.error("❌ No se encontró archivo .shp en el ZIP")
                return None
            
            # Read the shapefile
            gdf = gpd.read_file(shp_file)
            return gdf
            
    except Exception as e:
        st.error(f"❌ Error procesando shapefile: {str(e)}")
        return None

def process_geojson(uploaded_file):
    """Process uploaded GeoJSON file and return GeoDataFrame"""
    try:
        gdf = gpd.read_file(uploaded_file)
        return gdf
    except Exception as e:
        st.error(f"❌ Error procesando GeoJSON: {str(e)}")
        return None

def display_geodata_info(gdf, filename):
    """Display information about the GeoDataFrame"""
    st.success(f"✅ Archivo geoespacial cargado: **{filename}**")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Geometrías", len(gdf))
    with col2:
        st.metric("Columnas", len(gdf.columns))
    with col3:
        st.metric("CRS", str(gdf.crs) if gdf.crs else "No definido")
    with col4:
        geom_types = gdf.geometry.geom_type.unique()
        st.metric("Tipo geometría", ", ".join(geom_types))
    
    # Show attribute table
    st.subheader("📋 Tabla de Atributos")
    # Remove geometry column for display
    display_df = gdf.drop(columns=['geometry']) if 'geometry' in gdf.columns else gdf
    st.dataframe(display_df.head(10), use_container_width=True)
    
    # Show bounds
    bounds = gdf.total_bounds
    st.subheader("🗺️ Extensión Geográfica")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Min X (Oeste):** {bounds[0]:.6f}")
        st.write(f"**Min Y (Sur):** {bounds[1]:.6f}")
    with col2:
        st.write(f"**Max X (Este):** {bounds[2]:.6f}")
        st.write(f"**Max Y (Norte):** {bounds[3]:.6f}")

def create_folium_map(gdf, map_title="Mapa"):
    """Create a Folium map from GeoDataFrame"""
    # Ensure CRS is WGS84 for web mapping
    if gdf.crs != 'EPSG:4326':
        gdf_web = gdf.to_crs('EPSG:4326')
    else:
        gdf_web = gdf.copy()
    
    # Calculate center
    bounds = gdf_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )
    
    # Add GeoDataFrame to map
    folium.GeoJson(
        gdf_web.__geo_interface__,
        style_function=lambda feature: {
            'fillColor': 'blue',
            'color': 'black',
            'weight': 2,
            'fillOpacity': 0.3,
        },
        popup=folium.GeoJsonPopup(fields=list(gdf_web.columns[:-1]))  # Exclude geometry
    ).add_to(m)
    
    return m

def perform_spatial_clip(gdf_data, gdf_clip):
    """Perform spatial clipping operation"""
    try:
        # Ensure both GeoDataFrames have the same CRS
        if gdf_data.crs != gdf_clip.crs:
            st.info(f"🔄 Reproyectando datos de {gdf_data.crs} a {gdf_clip.crs}")
            gdf_data = gdf_data.to_crs(gdf_clip.crs)
        
        # Perform the clip
        clipped_gdf = gpd.clip(gdf_data, gdf_clip)
        
        return clipped_gdf
        
    except Exception as e:
        st.error(f"❌ Error en operación de recorte: {str(e)}")
        return None

def export_geodata(gdf, filename_base, format_type):
    """Export GeoDataFrame to different formats"""
    try:
        if format_type == "GeoJSON":
            geojson_str = gdf.to_json()
            return geojson_str, f"{filename_base}.geojson", "application/json"
        
        elif format_type == "Shapefile":
            # Create a temporary directory and zip file
            with tempfile.TemporaryDirectory() as temp_dir:
                shp_path = os.path.join(temp_dir, f"{filename_base}.shp")
                gdf.to_file(shp_path)
                
                # Create zip file
                zip_path = os.path.join(temp_dir, f"{filename_base}_shapefile.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file in os.listdir(temp_dir):
                        if file.startswith(filename_base) and not file.endswith('.zip'):
                            zipf.write(os.path.join(temp_dir, file), file)
                
                # Read zip file as bytes
                with open(zip_path, 'rb') as f:
                    zip_data = f.read()
                
                return zip_data, f"{filename_base}_shapefile.zip", "application/zip"
        
        elif format_type == "CSV":
            # Convert to regular DataFrame (lose geometry)
            df = pd.DataFrame(gdf.drop(columns=['geometry']))
            csv_data = df.to_csv(index=False)
            return csv_data, f"{filename_base}.csv", "text/csv"
            
    except Exception as e:
        st.error(f"❌ Error exportando datos: {str(e)}")
        return None, None, None
def display_file_info(uploaded_file, df):
    """Display information about the uploaded file"""
    st.success(f"✅ Archivo cargado: **{uploaded_file.name}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filas", len(df))
    with col2:
        st.metric("Columnas", len(df.columns))
    with col3:
        st.metric("Tamaño", f"{uploaded_file.size / 1024:.1f} KB")
    
    # Show basic info about the dataset
    st.subheader("📋 Información del Dataset")
    st.write("**Columnas:**")
    st.write(", ".join(df.columns.tolist()))
    
    st.write("**Primeras 5 filas:**")
    st.dataframe(df.head(), use_container_width=True)
    
    # Data types
    st.write("**Tipos de datos:**")
    dtype_df = pd.DataFrame({
        'Columna': df.dtypes.index,
        'Tipo': df.dtypes.values
    })
    st.dataframe(dtype_df, use_container_width=True, hide_index=True)
    
    # Basic statistics for numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        st.write("**Estadísticas básicas (columnas numéricas):**")
        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
    
    # Check for missing values
    missing_data = df.isnull().sum()
    if missing_data.sum() > 0:
        st.write("**Valores faltantes:**")
        missing_df = pd.DataFrame({
            'Columna': missing_data.index,
            'Valores faltantes': missing_data.values,
            'Porcentaje': (missing_data.values / len(df) * 100).round(2)
        })
        missing_df = missing_df[missing_df['Valores faltantes'] > 0]
        st.dataframe(missing_df, use_container_width=True, hide_index=True)

def process_uploaded_file(uploaded_file):
    """Process the uploaded file and return a DataFrame"""
    try:
        if uploaded_file.name.endswith('.csv'):
            # Try different encodings for CSV
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    uploaded_file.seek(0)  # Reset file pointer
                    df = pd.read_csv(uploaded_file, encoding='latin-1')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='cp1252')
        
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        
        elif uploaded_file.name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        
        elif uploaded_file.name.endswith('.parquet'):
            df = pd.read_parquet(uploaded_file)
        
        else:
            st.error("❌ Formato de archivo no soportado. Use CSV, Excel, JSON o Parquet.")
            return None
            
        return df
        
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {str(e)}")
        return None

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
        df_dgt = pd.read_parquet("dgt2023.parquet")
        df_dgt["municipio_completo"] = df_dgt["Código INE"].astype(str).str.zfill(5) + " " + df_dgt["Municipio"]
        return df, df_censo, df_hog_2011, df_hog_2021, df_censo2011, df_dgt
    except Exception as e:
        st.error(f"❌ No se pudieron cargar los archivos Parquet: {e}")
        return None, None, None, None, None, None

# -------------------- MAIN APP --------------------
st.title("📊 Indicadores INE por Municipio")

# Add tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["📈 Análisis INE", "📁 Subir Archivo", "🗺️ Análisis Geoespacial"])

with tab2:
    st.header("📁 Cargar y Analizar Archivo")
    st.markdown("Sube tu archivo CSV, Excel, JSON o Parquet para analizarlo:")
    
    uploaded_file = st.file_uploader(
        "Selecciona un archivo",
        type=['csv', 'xlsx', 'xls', 'json', 'parquet'],
        help="Formatos soportados: CSV, Excel (.xlsx, .xls), JSON, Parquet"
    )
    
    if uploaded_file is not None:
        with st.spinner('Procesando archivo...'):
            df_uploaded = process_uploaded_file(uploaded_file)
            
        if df_uploaded is not None:
            display_file_info(uploaded_file, df_uploaded)
            
            # Option to download processed data
            st.markdown("---")
            st.subheader("💾 Descargar Datos Procesados")
            
            col1, col2 = st.columns(2)
            with col1:
                csv_data = df_uploaded.to_csv(index=False)
                st.download_button(
                    "📥 Descargar como CSV",
                    csv_data,
                    f"processed_{uploaded_file.name.split('.')[0]}.csv",
                    "text/csv"
                )
            
            with col2:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_uploaded.to_excel(writer, index=False, sheet_name="Data")
                st.download_button(
                    "📊 Descargar como Excel",
                    buffer.getvalue(),
                    f"processed_{uploaded_file.name.split('.')[0]}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

with tab3:
    st.header("🗺️ Análisis Geoespacial")
    st.markdown("Sube archivos geoespaciales y realiza operaciones de recorte espacial:")
    
    # Initialize session state for geodata
    if 'gdf_data' not in st.session_state:
        st.session_state.gdf_data = None
    if 'gdf_clip' not in st.session_state:
        st.session_state.gdf_clip = None
    if 'clipped_result' not in st.session_state:
        st.session_state.clipped_result = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Archivo de Datos (para recortar)")
        st.markdown("Sube el archivo que quieres recortar (ej: datos de España)")
        
        data_file = st.file_uploader(
            "Selecciona archivo de datos",
            type=['geojson', 'zip'],
            help="Formatos: GeoJSON (.geojson) o Shapefile (.zip)",
            key="data_upload"
        )
        
        if data_file is not None:
            with st.spinner('Procesando archivo de datos...'):
                if data_file.name.endswith('.zip'):
                    gdf_data = process_shapefile(data_file)
                else:
                    gdf_data = process_geojson(data_file)
                
                if gdf_data is not None:
                    st.session_state.gdf_data = gdf_data
                    display_geodata_info(gdf_data, data_file.name)
                    
                    # Show map
                    st.subheader("🗺️ Vista del Dataset")
                    map_data = create_folium_map(gdf_data, "Datos a Recortar")
                    st_folium(map_data, width=400, height=300)
    
    with col2:
        st.subheader("✂️ Archivo de Recorte (máscara)")
        st.markdown("Sube el archivo que usarás como máscara (ej: municipio de Murcia)")
        
        clip_file = st.file_uploader(
            "Selecciona archivo de recorte",
            type=['geojson', 'zip'],
            help="Formatos: GeoJSON (.geojson) o Shapefile (.zip)",
            key="clip_upload"
        )
        
        if clip_file is not None:
            with st.spinner('Procesando archivo de recorte...'):
                if clip_file.name.endswith('.zip'):
                    gdf_clip = process_shapefile(clip_file)
                else:
                    gdf_clip = process_geojson(clip_file)
                
                if gdf_clip is not None:
                    st.session_state.gdf_clip = gdf_clip
                    display_geodata_info(gdf_clip, clip_file.name)
                    
                    # Show map
                    st.subheader("🗺️ Vista de la Máscara")
                    map_clip = create_folium_map(gdf_clip, "Máscara de Recorte")
                    st_folium(map_clip, width=400, height=300)
    
    # Clipping operation
    if st.session_state.gdf_data is not None and st.session_state.gdf_clip is not None:
        st.markdown("---")
        st.subheader("✂️ Operación de Recorte Espacial")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔥 Realizar Recorte", type="primary"):
                with st.spinner('Realizando recorte espacial...'):
                    clipped_gdf = perform_spatial_clip(st.session_state.gdf_data, st.session_state.gdf_clip)
                    
                    if clipped_gdf is not None:
                        st.session_state.clipped_result = clipped_gdf
                        st.success(f"✅ Recorte completado! {len(clipped_gdf)} geometrías resultantes")
        
        with col2:
            if st.session_state.clipped_result is not None:
                st.info(f"**Geometrías antes del recorte:** {len(st.session_state.gdf_data)}")
                st.info(f"**Geometrías después del recorte:** {len(st.session_state.clipped_result)}")
    
    # Show results
    if st.session_state.clipped_result is not None:
        st.markdown("---")
        st.subheader("📊 Resultado del Recorte")
        
        clipped_gdf = st.session_state.clipped_result
        
        # Show info about result
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Geometrías Resultantes", len(clipped_gdf))
        with col2:
            st.metric("Columnas", len(clipped_gdf.columns))
        with col3:
            st.metric("CRS", str(clipped_gdf.crs) if clipped_gdf.crs else "No definido")
        
        # Show attribute table
        st.subheader("📋 Tabla de Atributos del Resultado")
        display_df = clipped_gdf.drop(columns=['geometry']) if 'geometry' in clipped_gdf.columns else clipped_gdf
        st.dataframe(display_df, use_container_width=True)
        
        # Show map of result
        st.subheader("🗺️ Mapa del Resultado")
        result_map = create_folium_map(clipped_gdf, "Resultado del Recorte")
        st_folium(result_map, width=700, height=400)
        
        # Export options
        st.markdown("---")
        st.subheader("💾 Descargar Resultado")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Descargar GeoJSON"):
                data, filename, mime = export_geodata(clipped_gdf, "recorte_resultado", "GeoJSON")
                if data:
                    st.download_button(
                        "⬇️ GeoJSON",
                        data,
                        filename,
                        mime
                    )
        
        with col2:
            if st.button("📦 Descargar Shapefile"):
                data, filename, mime = export_geodata(clipped_gdf, "recorte_resultado", "Shapefile")
                if data:
                    st.download_button(
                        "⬇️ Shapefile (ZIP)",
                        data,
                        filename,
                        mime
                    )
        
        with col3:
            if st.button("📄 Descargar CSV"):
                data, filename, mime = export_geodata(clipped_gdf, "recorte_resultado", "CSV")
                if data:
                    st.download_button(
                        "⬇️ Tabla CSV",
                        data,
                        filename,
                        mime
                    )

with tab1:
    st.markdown("---")
    
    # Load original data
    data_loaded = load_data()
    if all(d is not None for d in data_loaded):
        df, df_censo, df_hog_2011, df_hog_2021, df_censo2011, df_dgt = data_loaded
    else:
        st.error("❌ No se pudieron cargar los datos base del INE")
        st.stop()

    # Constants
    YEARS = ["2024", "2023", "2022", "2021"]
    age_65_plus = ["65_69", "70_74", "75_79", "80_84", "85_89", "90_94", "95_99", "100"]
    age_85_plus = ["85_89", "90_94", "95_99", "100"]
    ages_0_14 = ["0_4", "5_9", "10_14"]
    ages_15_64 = ["15_19", "20_24", "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59", "60_64"]

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
            st.markdown("### ℹ️ Información Eje")
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

        censo_df = df_censo[df_censo["Municipio de residencia"].str.contains(selected_muni, case=False, na=False)]

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

        # Vehículos DGT
        df_dgt["municipio_completo"] = df_dgt["Código INE"].astype(str).str.zfill(5) + " " + df_dgt["Municipio"]
        dgt_row = df_dgt[df_dgt["municipio_completo"].str.lower() == selected_muni.lower()]

        try:
            turismos = dgt_row["Parque Turismos"].values[0]
            motos = dgt_row["Parque Motocicletas"].values[0]
            total_veh = dgt_row["Parque Total"].values[0]
            pop_2024 = pop_df["total_total_total_2024"].values[0]

            veh_1000hab = round((turismos + motos) / pop_2024 * 1000, 2) if pop_2024 else None
            pct_turismos = round(turismos / total_veh * 100, 2) if total_veh else None
            pct_motos = round(motos / total_veh * 100, 2) if total_veh else None
        except:
            veh_1000hab = None
            pct_turismos = None
            pct_motos = None

        # Result table
        results = []

        # -------------------- CALCULATE POPULATION VARIATION FOR EACH YEAR --------------------
        pop_variation_dict = {}

        try:
            hist_df_raw = pd.read_parquet("population/poblacion_completa.parquet")
            hist_df_raw.rename(columns={hist_df_raw.columns[0]: "municipio"}, inplace=True)
            hist_row = hist_df_raw[hist_df_raw["municipio"].str.contains(selected_muni, case=False, na=False)]

            if not hist_row.empty:
                hist_row = hist_row.iloc[0]

                def clean_series(series):
                    return pd.to_numeric(series.replace(r"^\s*$", pd.NA, regex=True), errors="coerce")

                pop_t = clean_series(hist_row.filter(like="_t")).dropna()
                pop_years = [int(col.split("_")[0]) for col in pop_t.index]
                pop_series = pd.Series(pop_t.values, index=pop_years).sort_index()

                for year in YEARS:
                    y = int(year)
                    if y in pop_series.index and (y - 10) in pop_series.index:
                        base = pop_series[y - 10]
                        current = pop_series[y]
                        pct = round((current - base) / base * 100, 2) if base else None
                        pop_variation_dict[year] = pct
                    else:
                        pop_variation_dict[year] = None
        except:
            for year in YEARS:
                pop_variation_dict[year] = None

        for year in YEARS:
            total = pop_df.get(f"total_total_total_{year}", pd.Series([0])).values[0]
            over_65 = pop_df[[f"total_{age}_total_{year}" for age in age_65_plus if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
            over_85 = pop_df[[f"total_{age}_total_{year}" for age in age_85_plus if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
            foreign = pop_df.get(f"total_total_EX_{year}", pd.Series([0])).values[0]
            pop_0_14 = pop_df[[f"total_{age}_total_{year}" for age in ages_0_14 if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]
            pop_15_64 = pop_df[[f"total_{age}_total_{year}" for age in ages_15_64 if f"total_{age}_total_{year}" in pop_df.columns]].sum(axis=1).values[0]

            row = {
                "Año": year,
                "Variación Poblacional Últimos 10 años (%)": pop_variation_dict.get(year),
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
                "VIVIENDA VACÍA 2011 (%)": viv_vacia_pct_2011 if year == "2021" else None,
                "D.18.a. Vehículos domiciliados cada 1000 hab.": veh_1000hab if year == "2024" else None,
                "D.18.b. % Turismos": pct_turismos if year == "2023" else None,
                "D.18.c. % Motocicletas": pct_motos if year == "2023" else None
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

        # -------------------- HISTORICAL POPULATION GRAPH --------------------
        try:
            hist_df_raw = pd.read_parquet("population/poblacion_completa.parquet")
            hist_df_raw.rename(columns={hist_df_raw.columns[0]: "municipio"}, inplace=True)
            hist_row = hist_df_raw[hist_df_raw["municipio"].str.contains(selected_muni, case=False, na=False)]
            if not hist_row.empty:
                hist_row = hist_row.iloc[0]

                def clean_series(series):
                    return pd.to_numeric(series.replace(r"^\s*$", pd.NA, regex=True), errors="coerce")

                pop_t = clean_series(hist_row.filter(like="_t")).dropna()
                pop_h = clean_series(hist_row.filter(like="_h")).dropna()
                pop_m = clean_series(hist_row.filter(like="_m")).dropna()

                def extract_years(series):
                    return [int(col.split("_")[0]) for col in series.index]

                years = extract_years(pop_t)

                hist_df = pd.DataFrame({
                    "Año": years,
                    "Total": pop_t.values,
                    "Hombres": pop_h.values if len(pop_h) else [None] * len(years),
                    "Mujeres": pop_m.values if len(pop_m) else [None] * len(years)
                }).sort_values("Año")

                st.markdown("### 📉 Evolución Histórica de la Población")
                st.line_chart(hist_df.set_index("Año"))

            else:
                st.warning("⚠️ No hay datos históricos disponibles para este municipio.")

        except Exception as e:
            st.error(f"❌ Error cargando datos históricos de población: {e}")

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
            st.metric("Indicadores", "15")

st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        📊 Aplicación de Indicadores INE por Municipio<br>
        Datos del Instituto Nacional de Estadística (INE)
    </div>
    """, unsafe_allow_html=True)