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
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = urllib.request.urlopen(url, timeout=10)
    data = json.loads(response.read())
    price = float(data["price"])

    st.metric(
        "Preço atual",
        f"${price:,.2f}"
    )

    st.success("🟢 Mercado conectado")

except Exception as e:
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
