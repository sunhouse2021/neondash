# dashboard.py – cloud ready (no winsound)
import streamlit as st
import pandas as pd
import ccxt, ta, time, os, csv, requests
from datetime import datetime

# ---------- clés testnet ----------
API_KEY = 'H8bHeeAtIO7MFiKXumwRqbZDuhwKg8m3BuY0M7YsYIoQWIPSRF4VuiA3oVvJfNpX'
API_SEC = 'MzO8yBW8MYjD7q0sNJOIuZDpM6UwPCKqwI9BvJAnMoPwkHOGmTg6a7hz1q4oanCK'
LOG_FILE  = 'trades_fake.csv'
TOKEN     = '7454759494:AAFD6y_UHa-pG-Jq3xQT5TM4E5LubBRHwpI'
CHAT_ID   = '6313144414'

exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SEC, 'enableRateLimit': True})
exchange.set_sandbox_mode(True)

# ---------- multilingue ----------
texts = {
    'fr': {'title': "Bot Néon – Dashboard", 'start': "▶️", 'stop': "⏹️", 'state_on': "🟢 ACTIF", 'state_off': "🔴 INACTIF",
           'price': "Prix", 'signal': "Signal", 'time': "Heure", 'stats': "Statistiques", 'nb_trades': "Trades", 'avg_time': "Temps moyen",
           'last_entry': "Dernier prix", 'trades': "Derniers trades", 'refresh': "🔄", 'no_trade': "Aucun trade.", 'exec': "Signal {} exécuté !"},
    'en': {'title': "Neon Bot – Dashboard", 'start': "▶️", 'stop': "⏹️", 'state_on': "🟢 ACTIVE", 'state_off': "🔴 INACTIVE",
           'price': "Price", 'signal': "Signal", 'time': "Time", 'stats': "Statistics", 'nb_trades': "Trades", 'avg_time': "Avg time",
           'last_entry': "Last entry", 'trades': "Last trades", 'refresh': "🔄", 'no_trade': "No trade.", 'exec': "Signal {} executed !"},
    'ar': {'title': "بوت نيون – لوحة التحكم", 'start': "▶️", 'stop': "⏹️", 'state_on': "🟢 نشط", 'state_off': "🔴 غير نشط",
           'price': "السعر", 'signal': "الإشارة", 'time': "الوقت", 'stats': "الإحصائيات", 'nb_trades': "الصفقات", 'avg_time': "متوسط الوقت",
           'last_entry': "آخر سعر", 'trades': "آخر الصفقات", 'refresh': "🔄", 'no_trade': "لا توجد صفقات.", 'exec': "تم تنفيذ الإشارة {} !"}
}

lang = st.sidebar.selectbox("🌐 Language", options=['fr', 'en', 'ar'])
t = texts[lang]

# ---------- sidebar ----------
st.sidebar.markdown("## ⚙️ Settings")
interval = st.sidebar.selectbox("⏰ Interval", ['1m', '5m', '15m', '1h'])
crypto   = st.sidebar.selectbox("💰 Crypto", ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT'])

st.markdown(f"# 🌌 {t['title']}")
st.markdown(f"**{crypto}** @ **{interval}**")

# ---------- trading engine ----------
def get_candles(symbol, timeframe, limit=100):
    bars = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    return df

def signal(df):
    df['sma10'] = ta.trend.sma_indicator(df['c'], 10)
    df['sma30'] = ta.trend.sma_indicator(df['c'], 30)
    last = df.iloc[-1]
    return 'buy' if last['sma10'] > last['sma30'] else ('sell' if last['sma30'] > last['sma10'] else 'neutral')

def place_sl_tp(entry_price, side):
    sl_price = round(entry_price * (0.99 if side == 'buy' else 1.01), 2)
    tp_price = round(entry_price * (1.02 if side == 'buy' else 0.98), 2)
    return sl_price, tp_price

def place_order(sig, price):
    qty = 0.001
    try:
        order = exchange.create_order(crypto, 'market', sig, qty)
        oid   = order['id']
        avg_p = order['average'] or price
        sl_p, tp_p = place_sl_tp(avg_p, sig)
        msg = f"✅ {sig} {qty} {crypto} @ {avg_p:.2f}  |  SL: {sl_p}  |  TP: {tp_p}"
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
        # Beep Linux (ou silence)
        print("\a")
        with open(LOG_FILE, 'a', newline='') as f:
            csv.writer(f).writerow([datetime.now(), avg_p, sig, qty, oid, sl_p, tp_p])
        return avg_p, sl_p, tp_p
    except Exception as e:
        st.error(f"Order error: {e}")
        return None, None, None

def stats():
    if not os.path.exists(LOG_FILE):
        return 0, None, None, None
    df = pd.read_csv(LOG_FILE)
    if df.empty:
        return 0, None, None, None
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['gain_pct'] = df.apply(lambda row: ((row['tp_price'] - row['price']) / row['price'] * 100)
                              if pd.notnull(row['tp_price']) else None, axis=1)
    avg_gain = df['gain_pct'].mean()
    avg_time = (df['datetime'].diff().dropna().mean()).total_seconds() / 60
    return len(df), avg_gain, avg_time, df['price'].iloc[-1]

def read_trades(n=10):
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    return pd.read_csv(LOG_FILE).tail(n)

# ---------- streamlit ----------
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_sig' not in st.session_state:
    st.session_state.last_sig = 'neutral'

col1, col2, col3 = st.columns(3)
with col1:
    if st.button(t['start']):
        st.session_state.running = True
with col2:
    if st.button(t['stop']):
        st.session_state.running = False
with col3:
    st.write(t['state_on'] if st.session_state.running else t['state_off'])

if st.session_state.running:
    df = get_candles(crypto, interval)
    sig = signal(df)
    price = df['c'].iloc[-1]
    st.metric(t['price'], f"{price:.2f} $")
    st.metric(t['signal'], sig.upper())
    st.metric(t['time'], datetime.now().strftime("%H:%M:%S"))

    # graph with SL/TP lines
    chart_df = df[['t', 'c']].copy()
    chart_df = chart_df.rename(columns={'t': 'index'}).set_index('index')
    if sig != 'neutral':
        sl_p, tp_p = place_sl_tp(price, sig)
        chart_df['SL'] = sl_p
        chart_df['TP'] = tp_p
    st.line_chart(chart_df)

    if sig != st.session_state.last_sig:
        res = place_order(sig, price)
        if res[0]:
            st.session_state.last_sig = sig
            st.success(t['exec'].format(sig))
    time.sleep(5)
    st.rerun()

nb, avg_gain, avg_time, last_p = stats()
st.subheader("🌌 " + t['stats'])
col4, col5, col6 = st.columns(3)
col4.metric(t['nb_trades'], nb)
col5.metric(t['last_entry'], f"{last_p:.2f}" if last_p else "-")
col6.metric(t['avg_time'], f"{avg_time:.1f} min" if avg_time else "-")
if avg_gain is not None:
    st.metric("📈 Gain moyen / trade", f"{avg_gain:.2f} %")

st.subheader("🌌 " + t['trades'])
trades = read_trades(10)
if trades.empty:
    st.info(t['no_trade'])
else:
    st.dataframe(trades)

if st.button(t['refresh']):
    st.rerun()
