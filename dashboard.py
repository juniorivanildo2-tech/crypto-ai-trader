import streamlit as st
import requests
import json
import os
from datetime import datetime

# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="🤖",
    layout="centered"
)

COINS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "Cardano": "cardano",
    "Dogecoin": "dogecoin"
}

LEARNING_FILE = "learning_data.json"


# =========================================================
# MOTOR DE MERCADO
# =========================================================

def get_market_data(crypto_id):

    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency=usd&ids={crypto_id}"
        "&price_change_percentage=1h,24h,7d"
    )

    response = requests.get(
        url,
        timeout=15,
        headers={"accept": "application/json"}
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        raise Exception("Nenhum dado recebido do mercado.")

    return data[0]


# =========================================================
# HISTÓRICO SIMPLIFICADO
# =========================================================

def get_history(crypto_id):

    url = (
        f"https://api.coingecko.com/api/v3/coins/"
        f"{crypto_id}/market_chart"
        "?vs_currency=usd&days=7&interval=hourly"
    )

    response = requests.get(
        url,
        timeout=15,
        headers={"accept": "application/json"}
    )

    response.raise_for_status()

    data = response.json()

    prices = [
        item[1]
        for item in data.get("prices", [])
    ]

    if len(prices) < 20:
        raise Exception("Histórico insuficiente para análise.")

    return prices


# =========================================================
# MÉDIA
# =========================================================

def moving_average(values, period):

    if len(values) < period:
        return None

    return sum(values[-period:]) / period


# =========================================================
# MOMENTUM
# =========================================================

def calculate_momentum(prices):

    if len(prices) < 6:
        return 0

    old_price = prices[-6]
    current_price = prices[-1]

    if old_price == 0:
        return 0

    return ((current_price - old_price) / old_price) * 100


# =========================================================
# MOTOR DE APRENDIZADO
# =========================================================

def load_learning():

    if not os.path.exists(LEARNING_FILE):
        return {
            "compra": 0,
            "venda": 0,
            "hold": 0,
            "acertos": 0,
            "erros": 0
        }

    try:

        with open(LEARNING_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception:

        return {
            "compra": 0,
            "venda": 0,
            "hold": 0,
            "acertos": 0,
            "erros": 0
        }


def save_learning(data):

    try:

        with open(
            LEARNING_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )

    except Exception:
        pass


def learning_adjustment(signal, learning):

    total = (
        learning["compra"]
        + learning["venda"]
        + learning["hold"]
    )

    if total == 0:
        return 0

    if signal == "COMPRA":
        value = learning["compra"]

    elif signal == "VENDA":
        value = learning["venda"]

    else:
        value = learning["hold"]

    return value / total


# =========================================================
# ANÁLISE
# =========================================================

def analyze_market(market, prices, learning):

    current_price = market["current_price"]

    change_1h = market.get(
        "price_change_percentage_1h_in_currency",
        0
    ) or 0

    change_24h = market.get(
        "price_change_percentage_24h",
        0
    ) or 0

    change_7d = market.get(
        "price_change_percentage_7d_in_currency",
        0
    ) or 0

    media_5 = moving_average(prices, 5)
    media_20 = moving_average(prices, 20)

    momentum = calculate_momentum(prices)

    score = 0

    # -----------------------------
    # MÉDIAS
    # -----------------------------

    if media_5 > media_20:
        score += 2

    elif media_5 < media_20:
        score -= 2

    # -----------------------------
    # MOMENTUM
    # -----------------------------

    if momentum > 0.20:
        score += 2

    elif momentum < -0.20:
        score -= 2

    # -----------------------------
    # 1 HORA
    # -----------------------------

    if change_1h > 0:
        score += 1

    elif change_1h < 0:
        score -= 1

    # -----------------------------
    # 24 HORAS
    # -----------------------------

    if change_24h > 1:
        score += 1

    elif change_24h < -1:
        score -= 1

    # -----------------------------
    # 7 DIAS
    # -----------------------------

    if change_7d > 2:
        score += 1

    elif change_7d < -2:
        score -= 1

    # -----------------------------
    # DECISÃO
    # -----------------------------

    if score >= 4:
        signal = "COMPRA"

    elif score <= -4:
        signal = "VENDA"

    else:
        signal = "HOLD"

    # -----------------------------
    # APRENDIZADO
    # -----------------------------

    adjustment = learning_adjustment(
        signal,
        learning
    )

    confidence = min(
        95,
        max(
            50,
            50 + abs(score) * 8
        )
    )

    # pequena influência do histórico
    if adjustment > 0.50:
        confidence += 3

    confidence = min(confidence, 95)

    # -----------------------------
    # EXPLICAÇÃO
    # -----------------------------

    if signal == "COMPRA":

        reason = (
            "O conjunto de indicadores apresenta "
            "predominância positiva. "
            "As médias, momentum e variações recentes "
            "favorecem uma possível alta."
        )

    elif signal == "VENDA":

        reason = (
            "O conjunto de indicadores apresenta "
            "predominância negativa. "
            "As médias, momentum e variações recentes "
            "favorecem uma possível baixa."
        )

    else:

        reason = (
            "Os indicadores estão misturados ou sem "
            "força suficiente para confirmar uma direção. "
            "O sistema prefere aguardar."
        )

    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "reason": reason,
        "price": current_price,
        "media_5": media_5,
        "media_20": media_20,
        "momentum": momentum,
        "change_1h": change_1h,
        "change_24h": change_24h,
        "change_7d": change_7d
    }


# =========================================================
# INTERFACE
# =========================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    "Paper Trading • Análise automática • Motor adaptativo"
)

st.divider()


# =========================================================
# ESCOLHA DA CRIPTO
# =========================================================

crypto_name = st.selectbox(
    "Criptomoeda",
    list(COINS.keys())
)

crypto_id = COINS[crypto_name]


# =========================================================
# BOTÃO DE ANÁLISE
# =========================================================

if st.button(
    "🔄 ANALISAR MERCADO",
    use_container_width=True
):

    try:

        with st.spinner(
            "Consultando o mercado..."
        ):

            market = get_market_data(
                crypto_id
            )

            prices = get_history(
                crypto_id
            )

            learning = load_learning()

            result = analyze_market(
                market,
                prices,
                learning
            )

            st.session_state["result"] = result
            st.session_state["crypto"] = crypto_name

    except Exception as e:

        st.error(
            "❌ Não foi possível realizar a análise."
        )

        st.warning(
            f"Detalhes: {e}"
        )


# =========================================================
# RESULTADO
# =========================================================

if "result" in st.session_state:

    result = st.session_state["result"]

    st.divider()

    st.header("🤖 Sinal do Trader")

    signal = result["signal"]

    st.subheader("Sinal atual")

    if signal == "COMPRA":

        st.success("🟢 COMPRA")

    elif signal == "VENDA":

        st.error("🔴 VENDA")

    else:

        st.warning("🟡 HOLD")

    st.metric(
        "Confiança",
        f'{result["confidence"]:.0f}%'
    )

    st.info(
        f'💡 {result["reason"]}'
    )

    st.divider()

    # =====================================================
    # DADOS DO MERCADO
    # =====================================================

    st.header("📊 Dados do Mercado")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Preço atual",
            f'${result["price"]:,.2f}'
        )

    with col2:

        st.metric(
            "Momentum",
            f'{result["momentum"]:.2f}%'
        )

    col3, col4 = st.columns(2)

    with col3:

        st.metric(
            "Média 5",
            f'${result["media_5"]:,.2f}'
        )

    with col4:

        st.metric(
            "Média 20",
            f'${result["media_20"]:,.2f}'
        )

    st.divider()

    st.header("📈 Variações")

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "1 hora",
            f'{result["change_1h"]:.2f}%'
        )

    with c2:

        st.metric(
            "24 horas",
            f'{result["change_24h"]:.2f}%'
        )

    with c3:

        st.metric(
            "7 dias",
            f'{result["change_7d"]:.2f}%'
        )

    st.divider()

    # =====================================================
    # SCORE
    # =====================================================

    st.header("🧠 Motor de Aprendizado")

    score = result["score"]

    if score > 0:

        st.write(
            f"Score de mercado: **+{score}**"
        )

    elif score < 0:

        st.write(
            f"Score de mercado: **{score}**"
        )

    else:

        st.write(
            "Score de mercado: **0**"
        )

    st.progress(
        min(
            1.0,
            max(
                0.0,
                (score + 8) / 16
            )
        )
    )

    learning = load_learning()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Compras registradas",
            learning["compra"]
        )

    with col2:

        st.metric(
            "Vendas registradas",
            learning["venda"]
        )

    with col3:

        st.metric(
            "HOLD registrados",
            learning["hold"]
        )

    st.caption(
        "O motor utiliza o histórico das decisões para "
        "ajustar gradualmente a confiança dos sinais."
    )


# =========================================================
# OPERAÇÃO SIMULADA
# =========================================================

st.divider()

st.header("💱 Operação Simulada")

valor = st.number_input(
    "Valor para comprar (US$)",
    min_value=10.0,
    value=1000.0,
    step=100.0
)

if st.button(
    "🟢 SIMULAR COMPRA",
    use_container_width=True
):

    if "result" not in st.session_state:

        st.warning(
            "Faça uma análise do mercado primeiro."
        )

    else:

        result = st.session_state["result"]

        price = result["price"]

        quantidade = valor / price

        st.success(
            "Operação simulada criada."
        )

        st.write(
            f"**Ativo:** {st.session_state['crypto']}"
        )

        st.write(
            f"**Valor:** US$ {valor:,.2f}"
        )

        st.write(
            f"**Preço:** US$ {price:,.2f}"
        )

        st.write(
            f"**Quantidade:** {quantidade:.8f}"
        )

        st.write(
            f"**Sinal no momento:** {result['signal']}"
        )


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "Crypto AI Trader V2 • Paper Trading"
)

st.caption(
    "Este sistema é experimental e não executa "
    "ordens reais."
)
