import streamlit as st
import pandas as pd
from gerar_mapa import gerar_mapa_filtrado
import datetime
from PIL import Image
import base64
from io import BytesIO

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode()
    return b64_data

# Carrega a imagem e exibe centralizada
with st.sidebar:
    image_base64 = get_base64_image("logo_souza_lima.png")
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{image_base64}' width='180'/>
        </div>
        <hr style='margin-top: 10px; margin-bottom: 20px;'>
        """,
        unsafe_allow_html=True
    )


st.markdown("""
            
    <style>
        /* Fundo geral */
        .main {
            background-color: #F7F7F7;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #041E42;
            border-right: 1px solid #E0E0E0;
        }

        /* Títulos */
        .css-10trblm, h1, h2, h3 {
            color: #041E42;
            font-weight: 800;
        }

        /* Texto geral */
        .css-15zrgzn, .css-1v0mbdj, p, label, span, div {
            color: #FFCD00;
        }

        /* Dropdowns */
        .stSelectbox > div > div {
            background-color: #041E42;
            color: #FFCD00;
        }

        /* Botões */
        .stButton>button {
            background-color: #FFCD00;
            color: #041E42;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            padding: 0.5rem 1rem;
        }

        .stButton>button:hover {
            background-color: #ffe84d;
            color: #041E42;
        }

        /* Métricas */
        .metric-label {
            color: #ffe84d !important;
        }

        .metric-value {
            color: #ffe84d !important;
            font-weight: bold;
        }

        /* Tabela e markdown */
        .stMarkdown {
            color: #ffe84d;
        }

        /* Mapa */
        .element-container iframe {
            border-radius: 12px;
            box-shadow: 0 0 8px rgba(0,0,0,0.15);
        }
    </style>
""", unsafe_allow_html=True)


st.set_page_config(layout="wide")

# Carrega os dados
df = pd.read_csv("BDV LATLONG PADRAO.csv", sep=";", encoding="ISO-8859-1")
df.columns = df.columns.str.strip()

# Converte colunas
df["DTHRCHEGADA"] = pd.to_datetime(df["DTHRCHEGADA"], errors="coerce")
df["DTHRSAIDA"] = pd.to_datetime(df["DTHRSAIDA"], errors="coerce")
df["DATA"] = df["DTHRCHEGADA"].dt.date

# Sidebar
st.sidebar.title("Filtros")

# Sidebar - filtro de funcionário
funcionarios = sorted(df["NOME_FUNCIONARIO"].dropna().unique().tolist())
nome_escolhido = st.sidebar.selectbox("Funcionário", funcionarios)

# Conversão da coluna DATA para date puro
df["DATA"] = pd.to_datetime(df["DATA"]).dt.date

# Datas disponíveis para o funcionário selecionado
datas_disponiveis = sorted(df[df["NOME_FUNCIONARIO"] == nome_escolhido]["DATA"].dropna().unique())

# Filtro de data com calendário
data_escolhida = st.sidebar.date_input(
    "Data",
    value=datas_disponiveis[0],
    min_value=datas_disponiveis[0],
    max_value=datas_disponiveis[-1]
)

# Validação: só continua se a data existir no histórico real
if data_escolhida not in datas_disponiveis:
    st.warning("⚠️ Essa data não tem marcações disponíveis.")
    st.stop()

# Filtra o DataFrame com base na seleção
df_filtrado = df[
    (df["NOME_FUNCIONARIO"] == nome_escolhido) &
    (df["DATA"] == data_escolhida)
]

html_mapa, resumo_rota = gerar_mapa_filtrado(df_filtrado)

with open(html_mapa, "r", encoding="utf-8") as f:
    mapa_html = f.read()

# Exibe título
st.title(f"Mapa BDV - {nome_escolhido} em {data_escolhida}")

# resumo
for f in resumo_rota["funcionarios"]:
    st.subheader(f"Resumo - {f['nome']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Distância total", f"{f['distancia_km']} km")
    col2.metric("Duração em Trânsito estimada", f"{f['duracao_min']} min")
    col3.metric("Marcações", f"{f['batidas']} pontos")

    if f["batidas"] > 1:
        st.markdown("**Tempos entre Marcações:**")
        for i, trecho in enumerate(f["tempos_entre_batidas"], 1):
            st.write(f"{i}. {trecho['origem']} → {trecho['destino']} = {trecho['minutos']} min")


# Exibe mapa
st.components.v1.html(mapa_html, height=800, width=1200, scrolling=False)