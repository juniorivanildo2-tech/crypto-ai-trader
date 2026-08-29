import streamlit as st
import urllib.request
import json

from paper_trader import PaperTrader


st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="₿",
    layout="wide"
)


# =========================
# CONTA VIRTUAL
# =========================

if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader(10000.0)

trader = st.session_state.trader


# =========================
# CABEÇALHO
# =========================

st.title("₿ Crypto AI Trader")
st.subheader("Paper Trading V2")

st.divider()


# =========================
# MERCADO
# =========================

st.header("📊 Mercado")

crypto = st.selectbox(
    "Escolha a criptomoeda",
    [
        "Bitcoin (BTC)",
        "Ethereum (ETH)",
        "Solana (SOL)"
    ]
)


ids = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana"
}


symbols = {
    "Bitcoin (BTC)": "BTCUSDT",
    "Ethereum (ETH)": "ETHUSDT",
    "Solana (SOL)": "SOLUSDT"
}


price = None


# =========================
# PREÇO ATUAL
# =========================

try:

    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids[crypto]}&vs_currencies=usd"
    )

    response = urllib.request.urlopen(url, timeout=10)

    data = json.loads(response.read().decode())

    price = float(data[ids[crypto]]["usd"])

    st.metric(
        "Preço atual",
        f"${price:,.2f}"
    )

    st.success("🟢 Mercado conectado")

except Exception as e:

    st.error(f"🔴 Erro na análise: {e}")


st.divider()


# =========================
# SINAL DO TRADER
# =========================

st.header("🤖 Sinal do Trader")


signal = "HOLD"
reason = "Aguardando análise do mercado."


if price is not None:

    try:

        symbol = symbols[crypto]

        url = (
            "https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval=5m&limit=20"
        )

        response = urllib.request.urlopen(url, timeout=10)

        candles = json.loads(
            response.read().decode()
        )

        closes = [
            float(candle[4])
            for candle in candles
        ]

        media_5 = sum(closes[-5:]) / 5
        media_20 = sum(closes[-20:]) / 20

        if media_5 > media_20 * 1.002:

            signal = "COMPRA"

            reason = (
                "Tendência de alta detectada "
                "pelas médias móveis."
            )

        elif media_5 < media_20 * 0.998:

            signal = "VENDA"

            reason = (
                "Tendência de baixa detectada "
                "pelas médias móveis."
            )

        else:

            signal = "HOLD"

            reason = (
                "Mercado sem tendência clara."
            )

    except Exception as e:

        signal = "HOLD"

        reason = (
            "Não foi possível realizar a análise."
        )


st.metric(
    "Sinal atual",
    signal
)

st.info(
    f"💡 {reason}"
)


st.divider()


# =========================
# OPERAÇÕES
# =========================

st.header("💱 Operação Simulada")

col1, col2 = st.columns(2)


with col1:

    valor_compra = st.number_input(
        "Valor para comprar (US$)",
        min_value=10.0,
        max_value=10000.0,
        value=1000.0,
        step=100.0
    )

    if st.button(
        "🟢 COMPRAR",
        use_container_width=True
    ):

        if price is not None:

            resultado = trader.comprar(
                price,
                valor_compra
            )

            st.success(resultado)

            st.rerun()

        else:

            st.error(
                "Preço indisponível."
            )


with col2:

    st.write("Venda toda a posição atual.")

    if st.button(
        "🔴 VENDER",
        use_container_width=True
    ):

        if price is not None:

            resultado = trader.vender(
                price
            )

            st.success(resultado)

            st.rerun()

        else:

            st.error(
                "Preço indisponível."
            )


st.divider()


# =========================
# CONTA VIRTUAL
# =========================

st.header("💰 Conta Virtual")


if price is not None:

    patrimonio = trader.patrimonio(price)

    resultado = trader.resultado(price)

else:

    patrimonio = trader.saldo
    resultado = 0.0


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Saldo disponível",
        f"${trader.saldo:,.2f}"
    )


with col2:

    st.metric(
        "Patrimônio",
        f"${patrimonio:,.2f}"
    )


with col3:

    st.metric(
        "Lucro / Prejuízo",
        f"${resultado:,.2f}"
    )


st.divider()


# =========================
# POSIÇÃO
# =========================

st.header("📦 Posição")


if trader.posicao > 0:

    st.write(
        f"Cripto: **{crypto}**"
    )

    st.write(
        f"Quantidade: **{trader.posicao:.6f}**"
    )

    st.write(
        f"Preço de entrada: "
        f"**${trader.preco_entrada:,.2f}**"
    )

else:

    st.write("Nenhuma posição aberta.")


st.divider()


st.caption(
    "⚠️ Paper Trading: todas as operações são simuladas."
)
