import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import requests
import re
import time

# ===============================
# Bot Configuration
# ===============================
TOKEN = "7009028228:AAHoN3yxLlZpezofquuyCIo3BQt9OxOr9Ms"  # <-- reemplaza aquí

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown", disable_web_page_preview=True)

# --- RPCs (usamos Helius como primario y Shyft como fallback) ---
HELIUS_API_KEY = "8f2678b0-a206-4090-9c02-7c76be9d136b"
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
SHYFT_API_KEY = "SMQG_9WjxOYl88xQ"
SHYFT_RPC_URL = f"https://rpc.shyft.to?api_key={SHYFT_API_KEY}"

# --- Enhanced APIs ---
HELIUS_TX_HISTORY = "https://api.helius.xyz/v0/addresses/{address}/transactions?api-key={api_key}&limit={limit}"
SHYFT_TX_HISTORY = "https://api.shyft.to/sol/v1/transaction/history?network=mainnet-beta&account={address}&limit={limit}"
SOLSCAN_TXS = "https://public-api.solscan.io/account/transactions?account={address}&limit={limit}"

# Tokens
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERiWJGTuL6YypA7AfgD5kZZgwyU5Yf3pqH"

# Filtros mínimos (para evitar ruido como casino/airdrops de 0 o polvo)
MIN_SOL = 0.05
MIN_STABLE = 0.01  # USDC/USDT

# Regex para detectar wallets + descripción opcional (en paréntesis o texto)
# Ejemplos válidos:
#   7Uioix... (dev 1 TETAS)
#   7Uioix... dev 1 TETAS
WALLET_REGEX = re.compile(
    r"([1-9A-HJ-NP-Za-km-z]{32,44})(?:\s*[()\s]+\s*(.+?)\s*[)]?\s*$|(?:\s+(.+))?)"
)

# -------------------------------
# Utils HTTP
# -------------------------------
def http_get(url, headers=None, timeout=15):
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
        if r.status_code == 429:
            # rate-limit: espera exponencial pequeña
            time.sleep(0.6)
            r = requests.get(url, headers=headers or {}, timeout=timeout)
        if r.ok:
            return r
    except Exception:
        pass
    return None

def http_post(url, json=None, headers=None, timeout=15):
    try:
        r = requests.post(url, json=json or {}, headers=headers or {}, timeout=timeout)
        if r.status_code == 429:
            time.sleep(0.6)
            r = requests.post(url, json=json or {}, headers=headers or {}, timeout=timeout)
        if r.ok:
            return r
    except Exception:
        pass
    return None

# -------------------------------
# Helpers para UI
# -------------------------------
def shorten_wallet(addr: str) -> str:
    """Abrevia direcciones largas para ahorrar espacio"""
    if len(addr) <= 12:
        return addr
    return f"{addr[:6]}...{addr[-6:]}"

def wallet_link(addr: str) -> str:
    """Devuelve un link clickeable a Solscan con la wallet abreviada"""
    return f"[{shorten_wallet(addr)}](https://solscan.io/account/{addr})"

# -------------------------------
# Balance (RPC con fallback)
# -------------------------------
def get_sol_balance(wallet):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet]}
    # Helius primero
    r = http_post(HELIUS_RPC_URL, json=payload)
    if r:
        try:
            return r.json()["result"]["value"] / 1e9
        except Exception:
            pass
    # Shyft fallback
    r2 = http_post(SHYFT_RPC_URL, json=payload)
    if r2:
        try:
            return r2.json()["result"]["value"] / 1e9
        except Exception:
            pass
    return 0.0

# -------------------------------
# Transfers via Helius (mejor fuente)
# -------------------------------
def get_transfers_helius(wallet, limit=10):
    url = HELIUS_TX_HISTORY.format(address=wallet, api_key=HELIUS_API_KEY, limit=max(50, limit))
    r = http_get(url)
    if not r:
        return []
    try:
        data = r.json()
        transfers = []

        for tx in data:
            # SOL nativo
            for nat in tx.get("nativeTransfers", []) or []:
                try:
                    amount_sol = float(nat.get("amount", 0)) / 1e9  # lamports -> SOL
                except Exception:
                    amount_sol = 0.0
                if amount_sol >= MIN_SOL:
                    src = nat.get("fromUserAccount") or nat.get("from")
                    dst = nat.get("toUserAccount") or nat.get("to")
                    # solo registramos si hay direcciones
                    if src and dst:
                        transfers.append(("SOL", src, dst, amount_sol))

            # SPL tokens (USDC/USDT)
            for t in tx.get("tokenTransfers", []) or []:
                mint = t.get("mint", "")
                if mint in (USDC_MINT, USDT_MINT):
                    try:
                        amt = float(t.get("tokenAmount", 0))
                    except Exception:
                        amt = 0.0
                    if amt >= MIN_STABLE:
                        src = t.get("fromUserAccount") or t.get("from")
                        dst = t.get("toUserAccount") or t.get("to")
                        symbol = "USDC" if mint == USDC_MINT else "USDT"
                        if src and dst:
                            transfers.append((symbol, src, dst, amt))

        # Orden descendente por "recientes" ya viene así normalmente, nos quedamos con los primeros
        return transfers[:limit]
    except Exception:
        return []

# -------------------------------
# Transfers via Shyft (backup)
# -------------------------------
def get_transfers_shyft(wallet, limit=10):
    url = SHYFT_TX_HISTORY.format(address=wallet, limit=max(50, limit))
    headers = {"x-api-key": SHYFT_API_KEY}
    r = http_get(url, headers=headers)
    if not r:
        return []
    try:
        result = r.json().get("result", []) or []
        transfers = []
        for tx in result:
            # Algunos tx traen "nativeTransfers" y "tokenTransfers"
            for nat in tx.get("nativeTransfers", []) or []:
                try:
                    amount_sol = float(nat.get("amount", 0)) / 1e9
                except Exception:
                    amount_sol = 0.0
                if amount_sol >= MIN_SOL:
                    src = nat.get("fromUserAccount") or nat.get("from")
                    dst = nat.get("toUserAccount") or nat.get("to")
                    if src and dst:
                        transfers.append(("SOL", src, dst, amount_sol))

            for t in tx.get("tokenTransfers", []) or []:
                mint = t.get("mint", "")
                if mint in (USDC_MINT, USDT_MINT):
                    try:
                        amt = float(t.get("tokenAmount", 0))
                    except Exception:
                        amt = 0.0
                    if amt >= MIN_STABLE:
                        src = t.get("fromUserAccount") or t.get("from")
                        dst = t.get("toUserAccount") or t.get("to")
                        symbol = "USDC" if mint == USDC_MINT else "USDT"
                        if src and dst:
                            transfers.append((symbol, src, dst, amt))
        return transfers[:limit]
    except Exception:
        return []

# -------------------------------
# Transfers via Solscan (backup)
# -------------------------------
def get_transfers_solscan(wallet, limit=10):
    url = SOLSCAN_TXS.format(address=wallet, limit=max(50, limit))
    r = http_get(url)
    if not r:
        return []
    try:
        data = r.json()
        transfers = []
        for tx in data:
            for instr in tx.get("parsedInstruction", []) or []:
                t = instr.get("type")
                if t == "transfer":
                    # SOL transfer
                    lamports = instr.get("lamport", 0) or instr.get("lamports", 0) or 0
                    try:
                        sol = float(lamports) / 1e9
                    except Exception:
                        sol = 0.0
                    if sol >= MIN_SOL:
                        src = instr.get("source") or instr.get("from")
                        dst = instr.get("destination") or instr.get("to")
                        if src and dst:
                            transfers.append(("SOL", src, dst, sol))
                elif t == "spl-transfer":
                    # SPL token, pero Solscan no siempre expone mint aquí
                    mint = instr.get("mint", "")
                    amount = instr.get("amount", 0)
                    try:
                        amt = float(amount)
                    except Exception:
                        amt = 0.0
                    if mint in (USDC_MINT, USDT_MINT) and amt >= MIN_STABLE:
                        src = instr.get("source") or instr.get("from")
                        dst = instr.get("destination") or instr.get("to")
                        symbol = "USDC" if mint == USDC_MINT else "USDT"
                        if src and dst:
                            transfers.append((symbol, src, dst, amt))
        return transfers[:limit]
    except Exception:
        return []

# -------------------------------
# Transfers via RPC puro (último fallback)
# -------------------------------
def get_transfers_rpc(wallet, limit=10):
    transfers = []
    before = None
    while len(transfers) < limit:
        params = {"limit": 50}
        if before:
            params["before"] = before
        payload = {
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [wallet, params]
        }
        # Helius RPC
        r = http_post(HELIUS_RPC_URL, json=payload)
        if not r:
            # Shyft RPC
            r = http_post(SHYFT_RPC_URL, json=payload)
            if not r:
                break
        try:
            signatures = r.json().get("result", []) or []
        except Exception:
            break
        if not signatures:
            break

        before = signatures[-1]["signature"]

        for sig in signatures:
            tx_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
                "params": [sig["signature"], {"encoding": "jsonParsed"}]
            }
            rr = http_post(HELIUS_RPC_URL, json=tx_payload)
            if not rr:
                rr = http_post(SHYFT_RPC_URL, json=tx_payload)
                if not rr:
                    continue
            try:
                tx = rr.json().get("result", None)
            except Exception:
                tx = None
            if not tx:
                continue

            # Parse instrucciones (system transfer y spl-token transfer)
            for instr in tx.get("transaction", {}).get("message", {}).get("instructions", []) or []:
                prog = instr.get("program")
                parsed = instr.get("parsed", {}) or {}
                if prog == "system" and parsed.get("type") == "transfer":
                    info = parsed.get("info", {}) or {}
                    try:
                        sol = float(info.get("lamports", 0)) / 1e9
                    except Exception:
                        sol = 0.0
                    if sol >= MIN_SOL:
                        src = info.get("source")
                        dst = info.get("destination")
                        if src and dst:
                            transfers.append(("SOL", src, dst, sol))
                elif prog == "spl-token" and parsed.get("type") == "transfer":
                    info = parsed.get("info", {}) or {}
                    mint = info.get("mint", "")
                    if mint in (USDC_MINT, USDT_MINT):
                        try:
                            amt = float(info.get("tokenAmount", {}).get("uiAmount", 0.0))
                        except Exception:
                            amt = 0.0
                        if amt >= MIN_STABLE:
                            src = info.get("source")
                            dst = info.get("destination")
                            symbol = "USDC" if mint == USDC_MINT else "USDT"
                            if src and dst:
                                transfers.append((symbol, src, dst, amt))

            if len(transfers) >= limit:
                break
        # respirito para no quemar rate limits
        time.sleep(0.15)

    return transfers[:limit]

# -------------------------------
# Orquestador de Fallbacks
# -------------------------------
def get_recent_transfers(wallet, limit=10):
    # Orden de preferencia: Helius -> Shyft -> Solscan -> RPC
    sources = [
        ("Helius", get_transfers_helius),
        ("Shyft", get_transfers_shyft),
        ("Solscan", get_transfers_solscan),
        ("RPC", get_transfers_rpc),
    ]
    for name, func in sources:
        txs = func(wallet, limit=limit)
        if txs:
            return txs, name
    return [], "None"

# -------------------------------
# UI Helpers
# -------------------------------
def main_keyboard():
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(KeyboardButton("🔎 Check wallets"))
    kb.add(KeyboardButton("ℹ️ Help"))
    return kb

def send_split_message(chat_id, text):
    MAX = 4096
    if len(text) <= MAX:
        bot.send_message(chat_id, text)
        return
    for i in range(0, len(text), MAX):
        bot.send_message(chat_id, text[i:i+MAX])

# -------------------------------
# Handlers
# -------------------------------
@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.send_message(
        message.chat.id,
        "👋 Welcome! Send me *one or multiple* Solana wallet addresses (optionally with descriptions).\n\n"
        "I’ll show their:\n"
        "• 💰 SOL balance\n"
        "• 🔄 Last SOL/USDC/USDT transfers\n\n"
        "Example:\n`7Uioix... (dev 1)`\n`9KK8Z... dev 2`\n`W4srk...`",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text and m.text.strip().lower().startswith("ℹ️"))
def handle_help(message):
    bot.send_message(
        message.chat.id,
        "📖 *How to use:*\n"
        "Paste *one or more* wallet addresses (each on a new line).\n\n"
        "I return:\n"
        "• 💰 SOL balance (via Helius/Shyft RPC)\n"
        "• 🔄 Last SOL/USDC/USDT transfers (Helius → Shyft → Solscan → RPC)\n\n"
        "✅ Tiny dust transfers are filtered out.\n\n"
        "Tip: Add descriptions in parentheses.\n"
        "Example:\n`7Uioix... (dev 1)`"
    )

@bot.message_handler(func=lambda m: True)
def handle_wallets(message):
    raw = message.text.strip()
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    wallets = []

    # Parse cada línea
    for ln in lines:
        m = WALLET_REGEX.match(ln)
        if not m:
            # Si la línea tiene solo la wallet sin descripción, intentamos capturarla igual
            only_wallet = re.match(r"^([1-9A-HJ-NP-Za-km-z]{32,44})$", ln)
            if only_wallet:
                wallets.append((only_wallet.group(1), ""))
            continue
        w = m.group(1)
        desc = (m.group(2) or m.group(3) or "").strip()
        wallets.append((w, desc))

    if not wallets and raw:
        # caso: un solo string wallet
        only_wallet = re.match(r"^([1-9A-HJ-NP-Za-km-z]{32,44})$", raw)
        if only_wallet:
            wallets = [(only_wallet.group(1), "")]
        else:
            bot.send_message(message.chat.id, "❌ Invalid wallet format. Please paste one wallet per line.")
            return

    # Procesar todas las wallets y juntar en una sola respuesta (particionado si excede 4096)
    out = []
    for wallet, desc in wallets:
        bal = get_sol_balance(wallet)
        header = f"👜 [Wallet](https://solscan.io/account/{wallet})\n`{wallet}`"
        if desc:
            header += f" _({desc})_"
        header += f"\n💰 *SOL Balance:* `{bal:.4f}`\n"
        out.append(header)

        txs, source = get_recent_transfers(wallet, limit=10)
        if not txs:
            out.append("❌ _No SOL/USDC/USDT transfers found._\n")
        else:
            out.append(f"🔄 *Recent transfers (via {source}):*\n")
            for token, src, dst, amt in txs:
                out.append(f"- *{token}*: `{amt:.4f}`\n   from {wallet_link(src)} ➡ to {wallet_link(dst)}\n")
        out.append("─────────────\n\n")

        # Pausa anti rate-limit entre wallets
        time.sleep(0.15)

    send_split_message(message.chat.id, "".join(out) or "No wallets detected.")

# -------------------------------
# Start Bot
# -------------------------------
if __name__ == "__main__":
    print("Bot started...")
    bot.polling(none_stop=True)
