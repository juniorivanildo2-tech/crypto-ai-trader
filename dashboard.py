import streamlit as st
import urllib.request
import json

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="₿",
    layout="wide"
)

st.title("₿ Crypto AI Trader")
st.subheader("Paper Trading V2")

st.divider()

st.header("📊 Mercado")

crypto = st.selectbox(
    "Escolha a criptomoeda",
    ["Bitcoin (BTC)", "Ethereum (ETH)", "Solana (SOL)"]
)

ids = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana"
}

try:
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

    st.divider()

    st.header("🤖 Sinal do Trader")

    # Análise técnica - Paper Trading V1
try:
    symbol = symbols[crypto]

    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval=5m&limit=30"
    )

    response = urllib.request.urlopen(url, timeout=10)
    candles = json.loads(response.read().decode())

    closes = [float(candle[4]) for candle in candles]

    preco = closes[-1]
    media_5 = sum(closes[-5:]) / 5
    media_20 = sum(closes[-20:]) / 20

    if media_5 > media_20 * 1.002:
        sinal = "COMPRA"
        reason = "Tendência de alta detectada."
    elif media_5 < media_20 * 0.998:
        sinal = "VENDA"
        reason = "Tendência de baixa detectada."
    else:
        sinal = "HOLD"
        reason = "Mercado sem tendência clara."

except Exception:
    sinal = "HOLD"
    reason = "Não foi possível realizar a análise agora."

st.metric("Sinal atual", sinal)

st.warning(
    f"🟡 {reason}"
)

except Exception:
    st.error("Não foi possível obter os dados do mercado.")

st.divider()

st.header("💰 Conta Virtual")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Saldo Virtual",
        "$10,000.00"
    )

with col2:
    st.metric(
        "Lucro/Prejuízo",
        "$0.00"
    )

with col3:
    st.metric(
        "Posição",
        "Nenhuma"
    )

st.divider()

st.header("📋 Status")

st.info(
    "🤖 Trader em modo PAPER TRADING. "
    "Nenhuma ordem real será enviada."
)
