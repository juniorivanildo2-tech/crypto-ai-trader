import streamlit as st
import json
import urllib.request
import urllib.parse
from datetime import datetime
from statistics import mean

# ============================================================
# CRYPTO AI TRADER V4
# Inteligência de mercado + Paper Trading + Motor de Aprendizado
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="🤖",
    layout="centered"
)

# ============================================================
# CONFIGURAÇÕES
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
# ESTADO DO APLICATIVO
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
        "BUY": {"wins": 0, "losses": 0},
        "SELL": {"wins": 0, "losses": 0}
    }

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

# ============================================================
# FUNÇÕES
# ============================================================

def get_json(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as e:
        raise Exception(f"Falha na conexão: {e}")


def get_market_data(coin_id):
    url = (
        "https://api.coingecko.com/api/v3/coins/"
        f"{urllib.parse.quote(coin_id)}/market_chart"
        "?vs_currency=usd&days=2&interval=hourly"
    )

    return get_json(url)


def calculate_sma(values, period):
    if len(values) < period:
        return None

    return mean(values[-period:])


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


def calculate_momentum(closes):
    if len(closes) < 6:
        return 0.0

    old_price = closes[-6]

    if old_price == 0:
        return 0.0

    return ((closes[-1] - old_price) / old_price) * 100


def calculate_volume_ratio(volumes):
    if len(volumes) < 21:
        return 1.0

    average_volume = mean(volumes[-21:-1])

    if average_volume == 0:
        return 1.0

    return volumes[-1] / average_volume


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

def learning_bonus(direction):
    data = st.session_state.learning[direction]

    total = data["wins"] + data["losses"]

    if total == 0:
        return 0.0

    accuracy = data["wins"] / total

    # Pequeno ajuste baseado no histórico.
    if accuracy >= 0.65:
        return 8.0

    if accuracy >= 0.55:
        return 4.0

    if accuracy <= 0.35:
        return -8.0

    if accuracy <= 0.45:
        return -4.0

    return 0.0


def update_learning(direction, won):
    if direction not in st.session_state.learning:
        return

    if won:
        st.session_state.learning[direction]["wins"] += 1
    else:
        st.session_state.learning[direction]["losses"] += 1


# ============================================================
# ANÁLISE
# ============================================================

def analyze_market(coin_id):

    data = get_market_data(coin_id)

    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])

    if len(prices) < 25:
        raise Exception("Dados insuficientes para análise.")

    closes = [float(item[1]) for item in prices]
    volume_values = [float(item[1]) for item in volumes]

    current_price = closes[-1]

    sma5 = calculate_sma(closes, 5)
    sma20 = calculate_sma(closes, 20)

    rsi = calculate_rsi(closes)
    momentum = calculate_momentum(closes)
    volume_ratio = calculate_volume_ratio(volume_values)

    # --------------------------------------------------------
    # SISTEMA DE PONTUAÇÃO
    # --------------------------------------------------------

    buy_score = 0.0
    sell_score = 0.0

    reasons_buy = []
    reasons_sell = []

    # Médias móveis
    if sma5 > sma20 * 1.002:
        buy_score += 25
        reasons_buy.append("Média curta acima da média longa")

    elif sma5 < sma20 * 0.998:
        sell_score += 25
        reasons_sell.append("Média curta abaixo da média longa")

    # RSI
    if rsi < 35:
        buy_score += 20
        reasons_buy.append("RSI indica região de sobrevenda")

    elif rsi > 65:
        sell_score += 20
        reasons_sell.append("RSI indica região de sobrecompra")

    else:
        # RSI neutro
        if rsi >= 50:
            buy_score += 8
        else:
            sell_score += 8

    # Momentum
    if momentum > 0.20:
        buy_score += 20
        reasons_buy.append("Momentum positivo")

    elif momentum < -0.20:
        sell_score += 20
        reasons_sell.append("Momentum negativo")

    # Volume
    if volume_ratio > 1.20:
        if momentum > 0:
            buy_score += 10
            reasons_buy.append("Volume acima da média com movimento positivo")
        elif momentum < 0:
            sell_score += 10
            reasons_sell.append("Volume acima da média com movimento negativo")

    # --------------------------------------------------------
    # APRENDIZADO
    # --------------------------------------------------------

    buy_score += learning_bonus("BUY")
    sell_score += learning_bonus("SELL")

    # Limita pontuação
    buy_score = max(0, min(100, buy_score))
    sell_score = max(0, min(100, sell_score))

    # --------------------------------------------------------
    # DECISÃO
    # --------------------------------------------------------

    difference = abs(buy_score - sell_score)

    if buy_score >= 55 and buy_score > sell_score:
        signal = "COMPRA"

        confidence = min(
            95,
            55 + (difference * 0.7)
        )

        reason = "; ".join(reasons_buy)

        if not reason:
            reason = "Conjunto de indicadores favorece alta."

    elif sell_score >= 55 and sell_score > buy_score:
        signal = "VENDA"

        confidence = min(
            95,
            55 + (difference * 0.7)
        )

        reason = "; ".join(reasons_sell)

        if not reason:
            reason = "Conjunto de indicadores favorece baixa."

    else:
        signal = "HOLD"

        confidence = max(
            50,
            75 - difference
        )

        reason = (
            "Os indicadores estão misturados ou "
            "sem força suficiente para confirmar uma direção."
        )

    return {
        "price": current_price,
        "sma5": sma5,
        "sma20": sma20,
        "rsi": rsi,
        "momentum": momentum,
        "volume_ratio": volume_ratio,
        "buy_score": buy_score,
        "sell_score": sell_score,
        "signal": signal,
        "confidence": confidence,
        "reason": reason
    }


# ============================================================
# PAPER TRADING
# ============================================================

def open_position(signal, price, amount, stop_loss, take_profit):

    if amount <= 0:
        return False, "Valor inválido."

    if amount > st.session_state.balance:
        return False, "Saldo insuficiente."

    direction = "LONG" if signal == "COMPRA" else "SHORT"

    st.session_state.balance -= amount

    st.session_state.position = {
        "direction": direction,
        "signal": signal,
        "entry": price,
        "amount": amount,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "opened_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    return True, "Operação simulada aberta."


def close_position(price, reason):

    position = st.session_state.position

    if position is None:
        return

    entry = position["entry"]
    amount = position["amount"]
    direction = position["direction"]

    if direction == "LONG":
        variation = (price - entry) / entry
    else:
        variation = (entry - price) / entry

    pnl = amount * variation

    returned = amount + pnl

    st.session_state.balance += returned

    won = pnl > 0

    update_learning(
        "BUY" if direction == "LONG" else "SELL",
        won
    )

    st.session_state.trades.append({
        "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Direção": direction,
        "Entrada": entry,
        "Saída": price,
        "Resultado": pnl,
        "Motivo": reason
    })

    st.session_state.position = None


def check_position(price):

    position = st.session_state.position

    if position is None:
        return

    direction = position["direction"]

    if direction == "LONG":

        if price <= position["stop_loss"]:
            close_position(price, "Stop Loss")

        elif price >= position["take_profit"]:
            close_position(price, "Take Profit")

    else:

        if price >= position["stop_loss"]:
            close_position(price, "Stop Loss")

        elif price <= position["take_profit"]:
            close_position(price, "Take Profit")


# ============================================================
# INTERFACE
# ============================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    "V4 • Inteligência de mercado • Motor de aprendizado • Paper Trading"
)

st.divider()

# ============================================================
# SELEÇÃO DA CRIPTOMOEDA
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

    with st.spinner("Analisando o mercado..."):

        try:

            result = analyze_market(coin_id)

            st.session_state.last_analysis = result

            check_position(result["price"])

            st.success("🟢 Mercado analisado com sucesso.")

        except Exception as e:

            st.error(f"🔴 Não foi possível realizar a análise: {e}")


# ============================================================
# RESULTADO DA ANÁLISE
# ============================================================

if st.session_state.last_analysis:

    result = st.session_state.last_analysis

    st.divider()

    st.header("🤖 Sinal do Trader")

    signal = result["signal"]

    if signal == "COMPRA":
        st.success("🟢 COMPRA")

    elif signal == "VENDA":
        st.error("🔴 VENDA")

    else:
        st.warning("🟡 HOLD")

    st.metric(
        "Confiança",
        f"{result['confidence']:.0f}%"
    )

    st.info(
        f"💡 {result['reason']}"
    )

    # ========================================================
    # MERCADO
    # ========================================================

    st.divider()

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
            f"${result['sma5']:,.2f}"
        )

    with col2:
        st.metric(
            "Média 20",
            f"${result['sma20']:,.2f}"
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
    # SCORE
    # ========================================================

    st.header("🎯 Pontuação")

    st.progress(
        int(result["buy_score"]),
        text=f"Compra: {result['buy_score']:.0f}/100"
    )

    st.progress(
        int(result["sell_score"]),
        text=f"Venda: {result['sell_score']:.0f}/100"
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

if st.session_state.position:

    position = st.session_state.position

    st.info(
        f"📌 Posição aberta: {position['direction']}\n\n"
        f"Entrada: ${position['entry']:,.2f}\n\n"
        f"Valor: US$ {position['amount']:,.2f}\n\n"
        f"Stop Loss: ${position['stop_loss']:,.2f}\n\n"
        f"Take Profit: ${position['take_profit']:,.2f}"
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

            st.success("Posição fechada.")
            st.rerun()

else:

    amount = st.number_input(
        "Valor para operação (US$)",
        min_value=10.0,
        max_value=st.session_state.balance,
        value=min(1000.0, st.session_state.balance),
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
                "Primeiro clique em ANALISAR MERCADO."
            )

        else:

            result = st.session_state.last_analysis

            if result["signal"] == "HOLD":

                st.warning(
                    "O sistema recomenda HOLD. "
                    "Nenhuma operação foi aberta."
                )

            else:

                price = result["price"]

                if result["signal"] == "COMPRA":

                    stop_loss = price * (
                        1 - stop_percent / 100
                    )

                    take_profit = price * (
                        1 + take_percent / 100
                    )

                else:

                    stop_loss = price * (
                        1 + stop_percent / 100
                    )

                    take_profit = price * (
                        1 - take_percent / 100
                    )

                ok, message = open_position(
                    result["signal"],
                    price,
                    amount,
                    stop_loss,
                    take_profit
                )

                if ok:
                    st.success(
                        f"🟢 {message}"
                    )
                    st.rerun()
                else:
                    st.error(message)


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

st.divider()

st.header("🧠 Motor de Aprendizado")

buy_data = st.session_state.learning["BUY"]
sell_data = st.session_state.learning["SELL"]

total_wins = (
    buy_data["wins"] +
    sell_data["wins"]
)

total_losses = (
    buy_data["losses"] +
    sell_data["losses"]
)

total_operations = total_wins + total_losses

if total_operations > 0:

    accuracy = (
        total_wins /
        total_operations
    ) * 100

else:

    accuracy = 0.0

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Operações avaliadas",
        total_operations
    )

with col2:
    st.metric(
        "Taxa de acerto",
        f"{accuracy:.1f}%"
    )

st.write(
    f"🟢 Compras: {buy_data['wins']} acertos / "
    f"{buy_data['losses']} erros"
)

st.write(
    f"🔴 Vendas: {sell_data['wins']} acertos / "
    f"{sell_data['losses']} erros"
)

if total_operations == 0:

    st.info(
        "O motor ainda não possui histórico suficiente. "
        "À medida que as operações simuladas forem encerradas, "
        "ele começará a ajustar a confiança."
    )

else:

    st.success(
        "🧠 O histórico das operações está sendo usado "
        "para ajustar o sistema."
    )


# ============================================================
# HISTÓRICO
# ============================================================

st.divider()

st.header("📋 Histórico")

if st.session_state.trades:

    for trade in reversed(
        st.session_state.trades[-10:]
    ):

        pnl = trade["Resultado"]

        if pnl >= 0:
            st.success(
                f"🟢 {trade['Direção']} | "
                f"P&L: US$ {pnl:,.2f} | "
                f"{trade['Motivo']}"
            )

        else:
            st.error(
                f"🔴 {trade['Direção']} | "
                f"P&L: US$ {pnl:,.2f} | "
                f"{trade['Motivo']}"
            )

else:

    st.info(
        "Nenhuma operação encerrada ainda."
    )


# ============================================================
# AVISO
# ============================================================

st.divider()

st.caption(
    "⚠️ Este aplicativo utiliza Paper Trading. "
    "Nenhuma ordem real é enviada para uma corretora."
)
