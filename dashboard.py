import streamlit as st

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="₿",
    layout="wide"
)

st.title("₿ Crypto AI Trader")
st.subheader("Paper Trading V1")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Saldo Virtual", "$10,000.00")

with col2:
    st.metric("Lucro/Prejuízo", "$0.00")

with col3:
    st.metric("Posição", "Nenhuma")

st.divider()

st.header("📊 Mercado")

crypto = st.selectbox(
    "Escolha a criptomoeda",
    ["Bitcoin (BTC)", "Ethereum (ETH)", "Solana (SOL)"]
)

st.write("Criptomoeda selecionada:", crypto)

st.header("🤖 Sinal da IA")

st.info("HOLD — aguardando análise")

st.divider()

st.header("📜 Histórico de operações")

st.write("Nenhuma operação realizada.")

st.caption("⚠️ V1 em PAPER TRADING — nenhuma ordem real será enviada.")
