import streamlit as st
import requests
import pandas as pd
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="🤖",
    layout="wide"
)


# ============================================================
# CRIPTOMOEDAS
# ============================================================

COINS = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana",
    "BNB (BNB)": "binancecoin",
    "XRP (XRP)": "ripple",
    "Dogecoin (DOGE)": "dogecoin",
    "Cardano (ADA)": "cardano",
    "Avalanche (AVAX)": "avalanche-2",
    "Chainlink (LINK)": "chainlink",
    "Polkadot (DOT)": "polkadot"
}


# ============================================================
# FUNÇÃO: BUSCAR PREÇO
# ============================================================

def get_current_price(coin_id):
    url = "https://api.coingecko.com/api/v3/simple/price"

    params = {
        "ids": coin_id,
        "vs_currencies": "usd"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    return float(data[coin_id]["usd"])


# ============================================================
# FUNÇÃO: BUSCAR HISTÓRICO
# ============================================================

def get_market_history(coin_id):
    url = (
        f"https://api.coingecko.com/api/v3/coins/"
        f"{coin_id}/market_chart"
    )

    params = {
        "vs_currency": "usd",
        "days": "7"
    }

    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    prices = data.get("prices", [])

    if len(prices) < 25:
        raise ValueError(
            "Histórico insuficiente para realizar a análise."
        )

    df = pd.DataFrame(
        prices,
        columns=["timestamp", "price"]
    )

    df["datetime"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df = df.dropna()

    return df


# ============================================================
# FUNÇÃO: ANALISAR MERCADO
# ============================================================

def analyze_market(df):
    df = df.copy()

    df["media_5"] = (
        df["price"]
        .rolling(window=5)
        .mean()
    )

    df["media_20"] = (
        df["price"]
        .rolling(window=20)
        .mean()
    )

    df = df.dropna()

    if len(df) == 0:
        raise ValueError(
            "Não existem dados suficientes para análise."
        )

    ultimo = df.iloc[-1]

    preco = float(ultimo["price"])
    media_5 = float(ultimo["media_5"])
    media_20 = float(ultimo["media_20"])

    # --------------------------------------------------------
    # REGRAS DO SINAL
    # --------------------------------------------------------

    if media_5 > media_20 * 1.002:

        signal = "COMPRA"

        reason = (
            "Tendência de alta detectada. "
            "A média curta está acima da média longa."
        )

    elif media_5 < media_20 * 0.998:

        signal = "VENDA"

        reason = (
            "Tendência de baixa detectada. "
            "A média curta está abaixo da média longa."
        )

    else:

        signal = "HOLD"

        reason = (
            "Mercado sem tendência clara. "
            "As médias móveis estão próximas."
        )

    return signal, reason, preco, media_5, media_20, df


# ============================================================
# TÍTULO
# ============================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    "Sistema de análise de criptomoedas — V1 | Operação simulada"
)


# ============================================================
# BARRA LATERAL
# ============================================================

st.sidebar.header("⚙️ Configurações")

coin_name = st.sidebar.selectbox(
    "Escolha a criptomoeda",
    list(COINS.keys())
)

coin_id = COINS[coin_name]

st.sidebar.divider()

capital = st.sidebar.number_input(
    "Capital simulado (US$)",
    min_value=100.0,
    max_value=1000000.0,
    value=1000.0,
    step=100.0
)

st.sidebar.divider()

st.sidebar.info(
    "Este aplicativo trabalha somente com "
    "operações simuladas. Nenhuma ordem real "
    "é enviada para uma corretora."
)


# ============================================================
# ESTADO DO APLICATIVO
# ============================================================

if "paper_balance" not in st.session_state:
    st.session_state.paper_balance = capital

if "position" not in st.session_state:
    st.session_state.position = False

if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0.0

if "invested" not in st.session_state:
    st.session_state.invested = 0.0


# ============================================================
# BUSCAR MERCADO
# ============================================================

try:

    price = get_current_price(coin_id)

    market_connected = True

except Exception as e:

    market_connected = False
    price = None
    market_error = str(e)


# ============================================================
# PREÇO ATUAL
# ============================================================

if market_connected:

    st.metric(
        "💰 Preço atual",
        f"US$ {price:,.2f}"
    )

    st.success(
        "🟢 Mercado conectado"
    )

else:

    st.error(
        "🔴 Não foi possível conectar ao mercado."
    )

    st.code(market_error)


st.divider()


# ============================================================
# ANÁLISE
# ============================================================

st.header("🤖 Sinal do Trader")


if market_connected:

    try:

        history = get_market_history(coin_id)

        (
            signal,
            reason,
            analyzed_price,
            media_5,
            media_20,
            history
        ) = analyze_market(history)

        # ----------------------------------------------------
        # SINAL
        # ----------------------------------------------------

        if signal == "COMPRA":

            st.success("🟢 COMPRA")

        elif signal == "VENDA":

            st.error("🔴 VENDA")

        else:

            st.warning("🟡 HOLD")


        st.subheader(signal)

        st.info(
            f"💡 {reason}"
        )


        # ----------------------------------------------------
        # MÉTRICAS
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Preço",
                f"US$ {analyzed_price:,.2f}"
            )

        with col2:

            st.metric(
                "Média 5",
                f"US$ {media_5:,.2f}"
            )

        with col3:

            st.metric(
                "Média 20",
                f"US$ {media_20:,.2f}"
            )


        # ----------------------------------------------------
        # GRÁFICO
        # ----------------------------------------------------

        st.subheader("📈 Histórico do mercado")

        chart_data = history[
            ["datetime", "price", "media_5", "media_20"]
        ].copy()

        chart_data = chart_data.set_index(
            "datetime"
        )

        chart_data.columns = [
            "Preço",
            "Média 5",
            "Média 20"
        ]

        st.line_chart(chart_data)


    except Exception as e:

        st.error(
            "❌ Erro durante a análise."
        )

        st.code(str(e))

else:

    st.warning(
        "Aguardando conexão com o mercado."
    )


# ============================================================
# OPERAÇÃO SIMULADA
# ============================================================

st.divider()

st.header("💱 Operação Simulada")


col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Saldo simulado",
        f"US$ {st.session_state.paper_balance:,.2f}"
    )

with col2:

    if st.session_state.position:

        st.metric(
            "Posição",
            "COMPRADO"
        )

    else:

        st.metric(
            "Posição",
            "FORA DO MERCADO"
        )


# ============================================================
# COMPRA SIMULADA
# ============================================================

if market_connected:

    if not st.session_state.position:

        buy_value = st.number_input(
            "Valor para comprar (US$)",
            min_value=10.0,
            max_value=float(
                st.session_state.paper_balance
            ),
            value=min(
                1000.0,
                float(st.session_state.paper_balance)
            ),
            step=10.0
        )

        if st.button(
            "🟢 COMPRAR",
            use_container_width=True
        ):

            if buy_value <= st.session_state.paper_balance:

                st.session_state.paper_balance -= buy_value

                st.session_state.position = True

                st.session_state.entry_price = price

                st.session_state.invested = buy_value

                st.success(
                    f"Compra simulada realizada por "
                    f"US$ {buy_value:,.2f}"
                )

                st.rerun()

    else:

        st.info(
            f"Você possui uma posição simulada "
            f"em {coin_name}."
        )

        st.write(
            f"Preço de entrada: "
            f"US$ {st.session_state.entry_price:,.2f}"
        )

        st.write(
            f"Valor investido: "
            f"US$ {st.session_state.invested:,.2f}"
        )


        # ----------------------------------------------------
        # VALOR ATUAL DA POSIÇÃO
        # ----------------------------------------------------

        current_value = (
            st.session_state.invested
            * price
            / st.session_state.entry_price
        )

        profit = (
            current_value
            - st.session_state.invested
        )

        if profit >= 0:

            st.success(
                f"🟢 Resultado: "
                f"+US$ {profit:,.2f}"
            )

        else:

            st.error(
                f"🔴 Resultado: "
                f"-US$ {abs(profit):,.2f}"
            )


        # ----------------------------------------------------
        # VENDA SIMULADA
        # ----------------------------------------------------

        if st.button(
            "🔴 VENDER",
            use_container_width=True
        ):

            st.session_state.paper_balance += current_value

            st.session_state.position = False

            st.session_state.entry_price = 0.0

            st.session_state.invested = 0.0

            st.success(
                f"Venda simulada realizada por "
                f"US$ {current_value:,.2f}"
            )

            st.rerun()


# ============================================================
# INFORMAÇÕES
# ============================================================

st.divider()

st.header("📊 Status do Sistema")

status_col1, status_col2 = st.columns(2)

with status_col1:

    st.write(
        f"**Criptomoeda:** {coin_name}"
    )

    st.write(
        "**Modo:** Paper Trading"
    )

with status_col2:

    st.write(
        "**Ordens reais:** DESATIVADAS"
    )

    st.write(
        f"**Última atualização:** "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )


# ============================================================
# AVISO
# ============================================================

st.divider()

st.caption(
    "⚠️ V1 experimental. Os sinais são baseados em "
    "médias móveis e não representam recomendação "
    "financeira. O sistema não executa operações reais."
)
