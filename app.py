import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Crypto AI Trader",
    page_icon="🤖",
    layout="wide"
)

LEARNING_FILE = "learning_data.json"

COINS = {
    "Bitcoin": "BTCUSDT",
    "Ethereum": "ETHUSDT",
    "BNB": "BNBUSDT",
    "Solana": "SOLUSDT",
    "XRP": "XRPUSDT",
    "Cardano": "ADAUSDT",
    "Dogecoin": "DOGEUSDT"
}

# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

def load_learning():
    default = {
        "total_analyses": 0,
        "wins": 0,
        "losses": 0,
        "signals": {
            "BUY": {"count": 0, "wins": 0},
            "SELL": {"count": 0, "wins": 0},
            "HOLD": {"count": 0, "wins": 0}
        },
        "weights": {
            "trend": 1.0,
            "rsi": 1.0,
            "macd": 1.0,
            "momentum": 1.0,
            "volume": 1.0
        }
    }

    try:
        if os.path.exists(LEARNING_FILE):
            with open(LEARNING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            for key in default:
                if key not in data:
                    data[key] = default[key]

            return data

    except Exception:
        pass

    return default


def save_learning(data):
    try:
        with open(LEARNING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


learning = load_learning()

# ============================================================
# DADOS DE MERCADO
# ============================================================

@st.cache_data(ttl=60)
def get_market_data(symbol, interval="1h", limit=300):

    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "buy_volume",
        "buy_quote_volume",
        "ignore"
    ]

    df = pd.DataFrame(data, columns=columns)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["timestamp"] = pd.to_datetime(
        df["open_time"],
        unit="ms"
    )

    return df


# ============================================================
# INDICADORES
# ============================================================

def calculate_indicators(df):

    df = df.copy()

    # SMA
    df["sma5"] = df["close"].rolling(5).mean()
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()

    # EMA
    df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

    # RSI
    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["macd"] = ema12 - ema26

    df["macd_signal"] = df["macd"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["macd_hist"] = (
        df["macd"] -
        df["macd_signal"]
    )

    # Momentum
    df["momentum"] = (
        df["close"].pct_change(10) * 100
    )

    # Volatilidade
    df["volatility"] = (
        df["close"].pct_change()
        .rolling(20)
        .std() * 100
    )

    # Volume médio
    df["volume_ma"] = (
        df["volume"]
        .rolling(20)
        .mean()
    )

    df["volume_ratio"] = (
        df["volume"] /
        df["volume_ma"]
    )

    return df


# ============================================================
# MOTOR DE ANÁLISE
# ============================================================

def analyze_market(df):

    latest = df.iloc[-1]

    score = 0.0
    max_score = 0.0

    reasons = []

    weights = learning["weights"]

    # --------------------------------------------------------
    # TENDÊNCIA
    # --------------------------------------------------------

    trend_weight = weights["trend"]

    if latest["ema9"] > latest["ema21"]:
        score += 2 * trend_weight
        reasons.append("Tendência de curto prazo positiva.")
    else:
        score -= 2 * trend_weight
        reasons.append("Tendência de curto prazo negativa.")

    max_score += 2 * trend_weight

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi = latest["rsi"]
    rsi_weight = weights["rsi"]

    if rsi < 30:
        score += 2 * rsi_weight
        reasons.append("RSI indica possível sobrevenda.")
    elif rsi > 70:
        score -= 2 * rsi_weight
        reasons.append("RSI indica possível sobrecompra.")
    elif rsi >= 50:
        score += 0.5 * rsi_weight
        reasons.append("RSI acima da região neutra.")
    else:
        score -= 0.5 * rsi_weight
        reasons.append("RSI abaixo da região neutra.")

    max_score += 2 * rsi_weight

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    macd_weight = weights["macd"]

    if latest["macd"] > latest["macd_signal"]:
        score += 2 * macd_weight
        reasons.append("MACD favorece movimento comprador.")
    else:
        score -= 2 * macd_weight
        reasons.append("MACD favorece movimento vendedor.")

    max_score += 2 * macd_weight

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    momentum_weight = weights["momentum"]

    if latest["momentum"] > 0:
        score += 1.5 * momentum_weight
        reasons.append("Momentum positivo.")
    else:
        score -= 1.5 * momentum_weight
        reasons.append("Momentum negativo.")

    max_score += 1.5 * momentum_weight

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    volume_weight = weights["volume"]

    if latest["volume_ratio"] > 1.2:

        if score > 0:
            score += 1 * volume_weight
            reasons.append("Volume acima da média confirma força compradora.")
        else:
            score -= 1 * volume_weight
            reasons.append("Volume acima da média confirma força vendedora.")

    max_score += 1 * volume_weight

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    percentage = (score / max_score) * 100

    if percentage >= 25:
        signal = "BUY"

    elif percentage <= -25:
        signal = "SELL"

    else:
        signal = "HOLD"

    confidence = min(
        95,
        max(
            50,
            int(50 + abs(percentage) * 0.45)
        )
    )

    return {
        "signal": signal,
        "confidence": confidence,
        "score": score,
        "percentage": percentage,
        "reasons": reasons
    }


# ============================================================
# APRENDIZADO
# ============================================================

def update_learning(signal, result):

    learning["total_analyses"] += 1

    if signal not in learning["signals"]:
        learning["signals"][signal] = {
            "count": 0,
            "wins": 0
        }

    learning["signals"][signal]["count"] += 1

    if result == "WIN":

        learning["wins"] += 1
        learning["signals"][signal]["wins"] += 1

        # Pequeno reforço
        for key in learning["weights"]:
            learning["weights"][key] *= 1.01

    elif result == "LOSS":

        learning["losses"] += 1

        # Pequena redução
        for key in learning["weights"]:
            learning["weights"][key] *= 0.99

    # Mantém pesos em uma faixa segura
    for key in learning["weights"]:
        learning["weights"][key] = min(
            2.0,
            max(
                0.5,
                learning["weights"][key]
            )
        )

    save_learning(learning)


def learning_accuracy():

    total = learning["wins"] + learning["losses"]

    if total == 0:
        return 0

    return round(
        (learning["wins"] / total) * 100,
        1
    )


# ============================================================
# PAPER TRADING
# ============================================================

if "balance" not in st.session_state:
    st.session_state.balance = 10000.0

if "position" not in st.session_state:
    st.session_state.position = None

if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0.0

if "trade_history" not in st.session_state:
    st.session_state.trade_history = []


def open_position(price, signal):

    if st.session_state.position is not None:
        return False

    st.session_state.position = signal
    st.session_state.entry_price = price

    return True


def close_position(price):

    if st.session_state.position is None:
        return None

    entry = st.session_state.entry_price

    if st.session_state.position == "BUY":

        profit_percent = (
            (price - entry) /
            entry
        ) * 100

    else:

        profit_percent = (
            (entry - price) /
            entry
        ) * 100

    profit_money = (
        st.session_state.balance *
        profit_percent /
        100
    )

    st.session_state.balance += profit_money

    result = "WIN" if profit_money > 0 else "LOSS"

    signal = st.session_state.position

    update_learning(signal, result)

    trade = {
        "data": datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        ),
        "tipo": signal,
        "entrada": round(entry, 2),
        "saida": round(price, 2),
        "resultado": result,
        "lucro": round(profit_money, 2)
    }

    st.session_state.trade_history.append(trade)

    st.session_state.position = None
    st.session_state.entry_price = 0.0

    return trade


# ============================================================
# INTERFACE
# ============================================================

st.title("🤖 Crypto AI Trader")

st.caption(
    "V4 • Inteligência de mercado • "
    "Motor de aprendizado • Paper Trading"
)

st.divider()

# ============================================================
# CONTROLE
# ============================================================

col1, col2 = st.columns(2)

with col1:

    coin_name = st.selectbox(
        "Criptomoeda",
        list(COINS.keys())
    )

with col2:

    interval = st.selectbox(
        "Período",
        ["15m", "1h", "4h", "1d"],
        index=1
    )

symbol = COINS[coin_name]

analyze_button = st.button(
    "🔄 ANALISAR MERCADO",
    use_container_width=True
)

# ============================================================
# ANÁLISE
# ============================================================

if analyze_button:

    try:

        with st.spinner(
            "Buscando dados e analisando o mercado..."
        ):

            df = get_market_data(
                symbol,
                interval,
                300
            )

            df = calculate_indicators(df)

            result = analyze_market(df)

            st.session_state.last_df = df
            st.session_state.last_result = result

        st.success(
            "✅ Mercado analisado com sucesso."
        )

    except Exception as e:

        st.error(
            "Não foi possível analisar o mercado."
        )

        st.info(
            "Verifique sua conexão com a internet "
            "e tente novamente."
        )


# ============================================================
# RESULTADO
# ============================================================

if "last_result" in st.session_state:

    result = st.session_state.last_result
    df = st.session_state.last_df

    st.divider()

    st.header("🤖 Sinal do Trader")

    signal = result["signal"]

    if signal == "BUY":

        st.success(
            "🟢 BUY — POSSÍVEL COMPRA"
        )

    elif signal == "SELL":

        st.error(
            "🔴 SELL — POSSÍVEL VENDA"
        )

    else:

        st.warning(
            "🟡 HOLD — AGUARDAR"
        )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Confiança",
            f'{result["confidence"]}%'
        )

    with col2:

        st.metric(
            "Score",
            f'{result["percentage"]:.1f}'
        )

    with col3:

        current_price = df.iloc[-1]["close"]

        st.metric(
            "Preço atual",
            f"${current_price:,.2f}"
        )

    st.info(
        "💡 " +
        " ".join(result["reasons"])
    )

    # ========================================================
    # INDICADORES
    # ========================================================

    st.divider()

    st.header("📊 Indicadores")

    latest = df.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "SMA 5",
            f"${latest['sma5']:,.2f}"
        )

    with c2:
        st.metric(
            "SMA 20",
            f"${latest['sma20']:,.2f}"
        )

    with c3:
        st.metric(
            "RSI",
            f"{latest['rsi']:.1f}"
        )

    with c4:
        st.metric(
            "Momentum",
            f"{latest['momentum']:.2f}%"
        )

    # ========================================================
    # GRÁFICO
    # ========================================================

    st.divider()

    st.header("📈 Gráfico")

    chart_data = df.set_index("timestamp")[
        ["close", "sma5", "sma20", "ema9", "ema21"]
    ]

    st.line_chart(
        chart_data,
        use_container_width=True
    )


# ============================================================
# PAPER TRADING
# ============================================================

st.divider()

st.header("💰 Paper Trading")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "Saldo disponível",
        f"US$ {st.session_state.balance:,.2f}"
    )

with col2:

    if st.session_state.position:

        st.metric(
            "Posição",
            st.session_state.position
        )

    else:

        st.metric(
            "Posição",
            "Nenhuma"
        )

with col3:

    if st.session_state.position:

        entry = st.session_state.entry_price

        if "last_df" in st.session_state:

            current = st.session_state.last_df.iloc[-1]["close"]

            if st.session_state.position == "BUY":

                pnl = (
                    (current - entry) /
                    entry
                ) * 100

            else:

                pnl = (
                    (entry - current) /
                    entry
                ) * 100

            st.metric(
                "Resultado atual",
                f"{pnl:.2f}%"
            )

    else:

        st.metric(
            "Resultado atual",
            "0.00%"
        )


col1, col2 = st.columns(2)

with col1:

    if st.button(
        "🟢 ABRIR OPERAÇÃO",
        use_container_width=True
    ):

        if "last_result" not in st.session_state:

            st.warning(
                "Faça uma análise primeiro."
            )

        elif st.session_state.position is not None:

            st.warning(
                "Já existe uma operação aberta."
            )

        else:

            current = st.session_state.last_df.iloc[-1]["close"]
            signal = st.session_state.last_result["signal"]

            if signal == "HOLD":

                st.warning(
                    "O sinal atual é HOLD. "
                    "O sistema recomenda aguardar."
                )

            else:

                open_position(
                    current,
                    signal
                )

                st.success(
                    f"Operação {signal} aberta em "
                    f"${current:,.2f}"
                )

with col2:

    if st.button(
        "🔴 FECHAR OPERAÇÃO",
        use_container_width=True
    ):

        if st.session_state.position is None:

            st.warning(
                "Não existe operação aberta."
            )

        elif "last_df" not in st.session_state:

            st.warning(
                "Faça uma nova análise primeiro."
            )

        else:

            current = st.session_state.last_df.iloc[-1]["close"]

            trade = close_position(current)

            if trade:

                if trade["resultado"] == "WIN":

                    st.success(
                        f"✅ Operação encerrada com lucro de "
                        f"US$ {trade['lucro']:.2f}"
                    )

                else:

                    st.error(
                        f"❌ Operação encerrada com prejuízo de "
                        f"US$ {trade['lucro']:.2f}"
                    )


# ============================================================
# MOTOR DE APRENDIZADO
# ============================================================

st.divider()

st.header("🧠 Motor de Aprendizado")

accuracy = learning_accuracy()

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Análises",
        learning["total_analyses"]
    )

with col2:

    st.metric(
        "Operações vencedoras",
        learning["wins"]
    )

with col3:

    st.metric(
        "Operações perdedoras",
        learning["losses"]
    )

with col4:

    st.metric(
        "Taxa de acerto",
        f"{accuracy}%"
    )

st.caption(
    "O motor ajusta gradualmente os pesos dos indicadores "
    "com base nos resultados das operações simuladas."
)

# ============================================================
# HISTÓRICO
# ============================================================

if st.session_state.trade_history:

    st.divider()

    st.header("📋 Histórico de Operações")

    history_df = pd.DataFrame(
        st.session_state.trade_history
    )

    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# RODAPÉ
# ============================================================

st.divider()

st.caption(
    "⚠️ Sistema experimental de Paper Trading. "
    "Nenhuma ordem real é enviada para uma corretora."
)
