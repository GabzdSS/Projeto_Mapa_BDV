import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard de Visitas", layout="wide")

# === Carregamento de dados ===
# Ajuste o caminho/arquivo se você trocar o CSV no futuro
CSV_PATH = "BDV LATLONG PADRAO.csv"
df = pd.read_csv(CSV_PATH, sep=";", encoding="ISO-8859-1")

# Garantir tipos
if "DTHRCHEGADA" in df.columns:
    df["DTHRCHEGADA"] = pd.to_datetime(df["DTHRCHEGADA"], errors="coerce")
df = df.dropna(subset=["DTHRCHEGADA"])

st.title("Dashboard de Visitas")

# === Filtros ===
with st.expander("Filtros", expanded=True):
    c1, c2, c3 = st.columns(3)

    # Usuários
    usuarios = sorted(df["NOME_FUNCIONARIO"].dropna().unique().tolist()) if "NOME_FUNCIONARIO" in df.columns else []
    # Clientes
    clientes = sorted(df["NOME_CLIENTE"].dropna().unique().tolist()) if "NOME_CLIENTE" in df.columns else []

    with c1:
        filtro_usuarios = st.multiselect(
            "Usuários",
            usuarios,
            default=usuarios[:5] if len(usuarios) > 5 else usuarios
        )
    with c2:
        filtro_clientes = st.multiselect(
            "Clientes",
            clientes,
            default=[]
        )
    with c3:
        min_dt = df["DTHRCHEGADA"].min().date()
        max_dt = df["DTHRCHEGADA"].max().date()
        dt_ini, dt_fim = st.date_input("Período", (min_dt, max_dt))

# Aplicar filtros
df_filtrado = df.copy()
if filtro_usuarios:
    df_filtrado = df_filtrado[df_filtrado["NOME_FUNCIONARIO"].isin(filtro_usuarios)]
if filtro_clientes:
    df_filtrado = df_filtrado[df_filtrado["NOME_CLIENTE"].isin(filtro_clientes)]
df_filtrado = df_filtrado[
    (df_filtrado["DTHRCHEGADA"].dt.date >= dt_ini) & (df_filtrado["DTHRCHEGADA"].dt.date <= dt_fim)
]

# === Métricas ===
total_visitas = len(df_filtrado)
visitas_unicas_clientes = df_filtrado["NOME_CLIENTE"].nunique() if "NOME_CLIENTE" in df_filtrado.columns else 0
visitas_unicas_usuarios = df_filtrado["NOME_FUNCIONARIO"].nunique() if "NOME_FUNCIONARIO" in df_filtrado.columns else 0

m1, m2, m3 = st.columns(3)
m1.metric("Total de visitas", f"{total_visitas}")
m2.metric("Clientes visitados (únicos)", f"{visitas_unicas_clientes}")
m3.metric("Usuários ativos (no período)", f"{visitas_unicas_usuarios}")

st.markdown("---")

# === Visitas por usuário ===
st.subheader("Visitas por usuário")
if "NOME_FUNCIONARIO" in df_filtrado.columns:
    visitas_por_usuario = (
        df_filtrado.groupby("NOME_FUNCIONARIO")
        .size()
        .sort_values(ascending=False)
        .rename("Visitas")
        .to_frame()
    )
    st.bar_chart(visitas_por_usuario)
else:
    st.info("Coluna NOME_FUNCIONARIO não encontrada no dataset.")

# === Clientes mais visitados (Top 10) ===
st.subheader("Clientes mais visitados (Top 10)")
if "NOME_CLIENTE" in df_filtrado.columns:
    clientes_mais = (
        df_filtrado.groupby("NOME_CLIENTE")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .rename("Visitas")
        .to_frame()
    )
    st.bar_chart(clientes_mais)
else:
    st.info("Coluna NOME_CLIENTE não encontrada no dataset.")

# === Visitas por data ===
st.subheader("Visitas por data")
df_filtrado["DATA"] = df_filtrado["DTHRCHEGADA"].dt.date
visitas_por_data = (
    df_filtrado.groupby("DATA")
    .size()
    .rename("Visitas")
    .to_frame()
    .sort_index()
)
st.line_chart(visitas_por_data)

# (Opcional) Tabela detalhe
st.markdown("---")
st.subheader("Detalhe das visitas (filtradas)")
cols_exibir = [c for c in ["DTHRCHEGADA","NOME_FUNCIONARIO","NOME_CLIENTE","CODIGOATIVO","DESCRICAO_ATIVO","BDV","BDVITEM"] if c in df_filtrado.columns]
st.dataframe(df_filtrado[cols_exibir].sort_values("DTHRCHEGADA", ascending=False), use_container_width=True)
