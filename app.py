import streamlit as st
import json
import urllib.request
import urllib.parse
from datetime import datetime
from statistics import mean

# ============================================================
# CRYPTO AI TRADER V4.1
# Motor adaptativo + Indicadores + Paper Trading
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader V4.1",
    page_icon="🤖",
    layout="centered"
)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

COINS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "BNB": "binancecoin",
    "Solana": "solana",
    "XRP": "ripple",
    "Cardano": "cardano",
    "Dogecoin": "dogecoin",
    "Avalanche": "avalanche-2",
    "Polkadot": "polkadot",
    "Chainlink": "chainlink"
}

# ============================================================
# MEMÓRIA DO SISTEMA
# ============================================================

if "balance" not in st.session_state:
    st.session_state.balance = 10000.0

if "initial_balance" not in st.session_state:
    st.session_state.initial_balance = 10000.0

if "position" not in st.session_state:
    st.session_state.position = None

if "trades" not in st.session_state:
    st.session_state.trades = []

if "learning" not in st.session_state:
    st.session_state.learning = {
        "COMPRA": {"acertos": 0, "erros": 0},
        "VENDA": {"acertos": 0, "erros": 0}
    }

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

# ============================================================
# FUNÇÃO DE INTERNET
# ============================================================

def get_json(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


# ============================================================
# DADOS DO MERCADO
# ============================================================

def get_market_data(coin_id):

    url = (
        "https://api.coingecko.com/api/v3/coins/"
        + urllib.parse.quote(coin_id)
        + "/market_chart"
        "?vs_currency=usd&days=2&interval=hourly"
    )

    return get_json(url)


# ============================================================
# MÉDIA MÓVEL
# ============================================================

def sma(values, period):

    if len(values) < period:
        return None

    return mean(values[-period:])


# ============================================================
# RSI
# ============================================================

def calculate_rsi(closes, period=14):

    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(-period, 0):

        change = closes[i] - closes[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = mean(gains)
    avg_loss = mean(losses)

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# ============================================================
# MOMENTUM
# ============================================================

def calculate_momentum(closes):

    if len(closes) < 6:
        return 0.0

    old_price = closes[-6]

    if old_price == 0:
        return 0.0

    return (
        (closes[-1] - old_price)
        / old_price
    ) * 100


# ============================================================
# VOLUME
# ============================================================

def calculate_volume_ratio(volumes):

    if len(volumes) < 21:
        return 1.0

    average = mean(volumes[-21:-1])

    if average == 0:
        return 1.0

    return volumes[-1] / average


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

def learning_accuracy(signal):

    data = st.session_state.learning[signal]

    total = (
        data["acertos"] +
        data["erros"]
    )

    if total == 0:
        return 50.0

    return (
        data["acertos"] /
        total
    ) * 100


def learning_adjustment(signal):

    data = st.session_state.learning[signal]

    total = (
        data["acertos"] +
        data["erros"]
    )

    if total < 2:
        return 0.0

    accuracy = learning_accuracy(signal)

    if accuracy >= 70:
        return 10.0

    if accuracy >= 60:
        return 5.0

    if accuracy <= 30:
        return -10.0

    if accuracy <= 40:
        return -5.0

    return 0.0


def register_learning(signal, profit):

    if signal not in st.session_state.learning:
        return

    if profit > 0:

        st.session_state.learning[
            signal
        ]["acertos"] += 1

    else:

        st.session_state.learning[
            signal
        ]["erros"] += 1


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analyze_market(coin_id):

    data = get_market_data(coin_id)

    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])

    if len(prices) < 25:
        raise Exception(
            "Dados insuficientes para análise."
        )

    closes = [
        float(item[1])
        for item in prices
    ]

    volume_values = [
        float(item[1])
        for item in volumes
    ]

    price = closes[-1]

    media5 = sma(closes, 5)
    media20 = sma(closes, 20)

    rsi = calculate_rsi(closes)

    momentum = calculate_momentum(
        closes
    )

    volume_ratio = calculate_volume_ratio(
        volume_values
    )

    # ========================================================
    # PONTUAÇÃO
    # ========================================================

    compra = 0.0
    venda = 0.0

    motivos_compra = []
    motivos_venda = []

    # --------------------------------------------------------
    # MÉDIAS
    # --------------------------------------------------------

    if media5 > media20 * 1.002:

        compra += 25

        motivos_compra.append(
            "Média 5 acima da Média 20"
        )

    elif media5 < media20 * 0.998:

        venda += 25

        motivos_venda.append(
            "Média 5 abaixo da Média 20"
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi < 35:

        compra += 20

        motivos_compra.append(
            "RSI em região de sobrevenda"
        )

    elif rsi > 65:

        venda += 20

        motivos_venda.append(
            "RSI em região de sobrecompra"
        )

    elif rsi >= 50:

        compra += 8

    else:

        venda += 8

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if momentum > 0.20:

        compra += 20

        motivos_compra.append(
            "Momentum positivo"
        )

    elif momentum < -0.20:

        venda += 20

        motivos_venda.append(
            "Momentum negativo"
        )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    if volume_ratio > 1.20:

        if momentum > 0:

            compra += 10

            motivos_compra.append(
                "Volume forte confirmando movimento"
            )

        elif momentum < 0:

            venda += 10

            motivos_venda.append(
                "Volume forte confirmando queda"
            )

    # ========================================================
    # APRENDIZADO
    # ========================================================

    ajuste_compra = learning_adjustment(
        "COMPRA"
    )

    ajuste_venda = learning_adjustment(
        "VENDA"
    )

    compra += ajuste_compra
    venda += ajuste_venda

    compra = max(
        0,
        min(100, compra)
    )

    venda = max(
        0,
        min(100, venda)
    )

    # ========================================================
    # DECISÃO
    # ========================================================

    diferenca = abs(
        compra - venda
    )

    if compra >= 55 and compra > venda:

        signal = "COMPRA"

        confidence = min(
            95,
            55 + diferenca * 0.7
        )

        reason = "; ".join(
            motivos_compra
        )

        if not reason:
            reason = (
                "Conjunto de indicadores "
                "favorece alta."
            )

    elif venda >= 55 and venda > compra:

        signal = "VENDA"

        confidence = min(
            95,
            55 + diferenca * 0.7
        )

        reason = "; ".join(
            motivos_venda
        )

        if not reason:
            reason = (
                "Conjunto de indicadores "
                "favorece baixa."
            )

    else:

        signal = "HOLD"

        confidence = max(
            50,
            75 - diferenca
        )

        reason = (
            "Os indicadores estão misturados "
            "ou sem força suficiente para "
            "confirmar uma direção."
        )

    return {
        "price": price,
        "media5": media5,
        "media20": media20,
        "rsi": rsi,
        "momentum": momentum,
        "volume_ratio": volume_ratio,
        "compra": compra,
        "venda": venda,
        "signal": signal,
        "confidence": confidence,
        "reason": reason
    }


# ============================================================
# ABRIR OPERAÇÃO
# ============================================================

def open_position(
    signal,
    price,
    amount,
    stop_percent,
    take_percent
):

    if amount <= 0:
        return False, "Valor inválido."

    if amount > st.session_state.balance:
        return False, "Saldo insuficiente."

    if signal == "COMPRA":

        direction = "LONG"

        stop_loss = price * (
            1 - stop_percent / 100
        )

        take_profit = price * (
            1 + take_percent / 100
        )

    else:

        direction = "SHORT"

        stop_loss = price * (
            1 + stop_percent / 100
        )

        take_profit = price * (
            1 - take_percent / 100
        )

    st.session_state.balance -= amount

    st.session_state.position = {

        "direction": direction,

        "signal": signal,

        "entry": price,

        "amount": amount,

        "stop_loss": stop_loss,

        "take_profit": take_profit,

        "opened_at":
            datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            )
    }

    return True, "Operação simulada aberta."


# ============================================================
# FECHAR OPERAÇÃO
# ============================================================

def close_position(price, reason):

    position = st.session_state.position

    if position is None:
        return

    entry = position["entry"]

    amount = position["amount"]

    direction = position["direction"]

    if direction == "LONG":

        variation = (
            price - entry
        ) / entry

    else:

        variation = (
            entry - price
        ) / entry

    profit = amount * variation

    returned = amount + profit

    st.session_state.balance += returned

    register_learning(
        position["signal"],
        profit
    )

    st.session_state.trades.append({

        "Data":
            datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            ),

        "Sinal":
            position["signal"],

        "Direção":
            direction,

        "Entrada":
            entry,

        "Saída":
            price,

        "Resultado":
            profit,

        "Motivo":
            reason
    })

    st.session_state.position = None


# ============================================================
# VERIFICAR STOP / TAKE
# ============================================================

def check_position(price):

    position = st.session_state.position

    if position is None:
        return

    if position["direction"] == "LONG":

        if price <= position["stop_loss"]:

            close_position(
                price,
                "Stop Loss"
            )

        elif price >= position["take_profit"]:

            close_position(
                price,
                "Take Profit"
            )

    else:

        if price >= position["stop_loss"]:

            close_position(
                price,
                "Stop Loss"
            )

        elif price <= position["take_profit"]:

            close_position(
                price,
                "Take Profit"
            )


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    "V4.1 • Motor adaptativo • "
    "Inteligência de mercado • Paper Trading"
)

st.divider()

# ============================================================
# ESCOLHA DA MOEDA
# ============================================================

coin_name = st.selectbox(
    "Criptomoeda",
    list(COINS.keys())
)

coin_id = COINS[coin_name]

if st.button(
    "🔄 ANALISAR MERCADO",
    use_container_width=True
):

    with st.spinner(
        "Analisando o mercado..."
    ):

        try:

            result = analyze_market(
                coin_id
            )

            st.session_state.last_analysis = result

            st.session_state.analysis_count += 1

            check_position(
                result["price"]
            )

            st.success(
                "✅ Mercado analisado com sucesso."
            )

        except Exception as e:

            st.error(
                f"🔴 Erro na análise: {e}"
            )


# ============================================================
# RESULTADO
# ============================================================

if st.session_state.last_analysis:

    result = st.session_state.last_analysis

    st.divider()

    st.header("🤖 Sinal do Trader")

    if result["signal"] == "COMPRA":

        st.success(
            "🟢 COMPRA"
        )

    elif result["signal"] == "VENDA":

        st.error(
            "🔴 VENDA"
        )

    else:

        st.warning(
            "🟡 HOLD"
        )

    st.metric(
        "Confiança",
        f"{result['confidence']:.0f}%"
    )

    st.info(
        "💡 " + result["reason"]
    )

    # ========================================================
    # MERCADO
    # ========================================================

    st.header("💰 Mercado")

    st.metric(
        "Preço atual",
        f"${result['price']:,.2f}"
    )

    # ========================================================
    # INDICADORES
    # ========================================================

    st.header("📊 Indicadores")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Média 5",
            f"${result['media5']:,.2f}"
        )

    with col2:

        st.metric(
            "Média 20",
            f"${result['media20']:,.2f}"
        )

    col3, col4 = st.columns(2)

    with col3:

        st.metric(
            "RSI",
            f"{result['rsi']:.1f}"
        )

    with col4:

        st.metric(
            "Momentum",
            f"{result['momentum']:.2f}%"
        )

    st.metric(
        "Volume / média",
        f"{result['volume_ratio']:.2f}x"
    )

    # ========================================================
    # PONTUAÇÃO
    # ========================================================

    st.header("🎯 Pontuação do Motor")

    st.progress(
        int(result["compra"]),
        text=(
            f"🟢 Compra: "
            f"{result['compra']:.0f}/100"
        )
    )

    st.progress(
        int(result["venda"]),
        text=(
            f"🔴 Venda: "
            f"{result['venda']:.0f}/100"
        )
    )


# ============================================================
# PAPER TRADING
# ============================================================

st.divider()

st.header("💰 Paper Trading")

st.metric(
    "Saldo disponível",
    f"US$ {st.session_state.balance:,.2f}"
)

# ============================================================
# POSIÇÃO ABERTA
# ============================================================

if st.session_state.position:

    position = st.session_state.position

    st.warning(
        f"📌 POSIÇÃO ABERTA — "
        f"{position['direction']}"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Entrada",
            f"${position['entry']:,.2f}"
        )

        st.metric(
            "Stop Loss",
            f"${position['stop_loss']:,.2f}"
        )

    with col2:

        st.metric(
            "Valor",
            f"US$ {position['amount']:,.2f}"
        )

        st.metric(
            "Take Profit",
            f"${position['take_profit']:,.2f}"
        )

    if st.button(
        "🔴 FECHAR POSIÇÃO",
        use_container_width=True
    ):

        if st.session_state.last_analysis:

            close_position(
                st.session_state.last_analysis["price"],
                "Fechamento manual"
            )

            st.success(
                "✅ Posição encerrada."
            )

            st.rerun()

else:

    amount = st.number_input(
        "Valor da operação (US$)",
        min_value=10.0,
        max_value=float(
            st.session_state.balance
        ),
        value=min(
            1000.0,
            st.session_state.balance
        ),
        step=50.0
    )

    stop_percent = st.slider(
        "Stop Loss (%)",
        0.5,
        10.0,
        2.0,
        0.5
    )

    take_percent = st.slider(
        "Take Profit (%)",
        0.5,
        20.0,
        4.0,
        0.5
    )

    if st.button(
        "🟢 ABRIR OPERAÇÃO SIMULADA",
        use_container_width=True
    ):

        if not st.session_state.last_analysis:

            st.warning(
                "Primeiro clique em "
                "ANALISAR MERCADO."
            )

        else:

            result = (
                st.session_state.last_analysis
            )

            if result["signal"] == "HOLD":

                st.warning(
                    "🟡 O motor recomenda HOLD. "
                    "Nenhuma operação foi aberta."
                )

            else:

                ok, message = open_position(
                    result["signal"],
                    result["price"],
                    amount,
                    stop_percent,
                    take_percent
                )

                if ok:

                    st.success(
                        "🟢 " + message
                    )

                    st.rerun()

                else:

                    st.error(message)


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

st.divider()

st.header("🧠 Motor de Aprendizado")

compra = st.session_state.learning["COMPRA"]
venda = st.session_state.learning["VENDA"]

total_acertos = (
    compra["acertos"] +
    venda["acertos"]
)

total_erros = (
    compra["erros"] +
    venda["erros"]
)

total = (
    total_acertos +
    total_erros
)

if total > 0:

    accuracy = (
        total_acertos /
        total
    ) * 100

else:

    accuracy = 0.0

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Análises",
        st.session_state.analysis_count
    )

with col2:

    st.metric(
        "Operações",
        total
    )

with col3:

    st.metric(
        "Acerto",
        f"{accuracy:.1f}%"
    )

st.write(
    f"🟢 COMPRA — "
    f"{compra['acertos']} acertos / "
    f"{compra['erros']} erros"
)

st.write(
    f"🔴 VENDA — "
    f"{venda['acertos']} acertos / "
    f"{venda['erros']} erros"
)

if total == 0:

    st.info(
        "🧠 O motor está começando sem histórico. "
        "Cada operação simulada encerrada ajudará "
        "a ajustar os próximos sinais."
    )

else:

    st.success(
        "🧠 O motor já está utilizando "
        "o histórico das operações."
    )


# ============================================================
# HISTÓRICO
# ============================================================

st.divider()

st.header("📋 Histórico de Operações")

if st.session_state.trades:

    for trade in reversed(
        st.session_state.trades[-10:]
    ):

        profit = trade["Resultado"]

        texto = (
            f"{trade['Data']} | "
            f"{trade['Sinal']} | "
            f"P&L: US$ {profit:,.2f} | "
            f"{trade['Motivo']}"
        )

        if profit > 0:

            st.success(
                "🟢 " + texto
            )

        elif profit < 0:

            st.error(
                "🔴 " + texto
            )

        else:

            st.info(
                "⚪ " + texto
            )

else:

    st.info(
        "Nenhuma operação encerrada ainda."
    )


# ============================================================
# RESULTADO GERAL
# ============================================================

st.divider()

profit_total = (
    st.session_state.balance -
    st.session_state.initial_balance
)

st.header("📈 Desempenho")

if profit_total >= 0:

    st.success(
        f"Resultado simulado: "
        f"+US$ {profit_total:,.2f}"
    )

else:

    st.error(
        f"Resultado simulado: "
        f"-US$ {abs(profit_total):,.2f}"
    )


# ============================================================
# SEGURANÇA
# ============================================================

st.divider()

st.caption(
    "⚠️ MODO PAPER TRADING. "
    "O aplicativo não envia ordens para corretoras "
    "e não movimenta dinheiro real."
)
