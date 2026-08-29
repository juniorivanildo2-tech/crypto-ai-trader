import streamlit as st
import urllib.request
import json

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="₿",
    layout="wide"
)

st.title("₿ Crypto AI Trader")
st.subheader("Paper Trading V1")

st.divider()

st.header("📊 Mercado")

crypto = st.selectbox(
    "Escolha a criptomoeda",
    ["Bitcoin (BTC)", "Ethereum (ETH)", "Solana (SOL)"]
)

symbols = {
    "Bitcoin (BTC)": "BTCUSDT",
    "Ethereum (ETH)": "ETHUSDT",
    "Solana (SOL)": "SOLUSDT"
}

symbol = symbols[crypto]

try:
    ids = {
        "Bitcoin (BTC)": "bitcoin",
        "Ethereum (ETH)": "ethereum",
        "Solana (SOL)": "solana"
    }

    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids[crypto]}&vs_currencies=usd"
    )

    response = urllib.request.urlopen(url, timeout=10)
    data = json.loads(response.read())

    price = float(data[ids[crypto]]["usd"])

    st.metric(
        "Preço atual",
        f"${price:,.2f}"
    )

    st.success("🟢 Mercado conectado")

except Exception:
    st.error("Não foi possível obter o preço agora.")

st.divider()

st.header("💰 Conta Virtual")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Saldo Virtual", "$10,000.00")

with col2:
    st.metric("Lucro/Prejuízo", "$0.00")

with col3:
    st.metric("Posição", "Nenhuma")

st.divider()

st.info("🤖 IA Trader: aguardando sinais de mercado...")
