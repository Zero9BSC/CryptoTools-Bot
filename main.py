import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import re
import base64
import struct
import time
from solders.pubkey import Pubkey

# Bot Configuration
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

# Solana RPC URL
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Token Info APIs
SOLANA_FM_API_URL = "https://api.solana.fm/v0/tokens/{}"
SOLSCAN_API_URL = "https://api.solscan.io/token/{}"

# Program IDs and Token Mints
METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERiWJGTuL6YypA7AfgD5kZZgwyU5Yf3pqH"

# User States
user_states = {}
user_languages = {}
wallet_descriptions = {}

# Wallet Regex
WALLET_REGEX = re.compile(r"([1-9A-HJ-NP-Za-km-z]{32,44})\s+(.+)")

# Language Texts
texts = {
    'en': {
        'start': "Welcome to *Solana Wallet Bot*! 🚀\n\nCommands:\n🔍 *View Tokens* - See tokens\n📄 *View Transfers* - See recent SOL/USDC/USDT transfers\n🌐 *Change Language* - Switch language\nℹ️ *About* - About this bot",
        'help': "*Available Commands:*\n🔍 *View Tokens*\n📄 *View Transfers*\n🌐 *Change Language*\nℹ️ *About*",
        'choose_language': "Please choose your language:",
        'tokens_prompt': "Send a wallet address or multiple addresses to check tokens.",
        'transfers_prompt': "Send a wallet address to check last transfers.",
        'wallet_invalid': "Invalid wallet address.",
        'no_tokens': "No tokens found in this wallet.",
        'no_recent_transfers': "No recent transfers found.",
        'balance': "*Wallet:* `{}`\n{}*SOL Balance:* `{:.4f}`\n\n",
        'recent_transfers': "Recent SOL, USDC and USDT transfers:\n",
        'about': "This bot was made for developers to easily inspect Solana wallets. Open source project."
    },
    'es': {
        'start': "¡Bienvenido al *Bot de Solana*! 🚀\n\nComandos:\n🔍 *Ver Tokens* - Ver tokens\n📄 *Ver Transferencias* - Ver transferencias de SOL/USDC/USDT\n🌐 *Cambiar Idioma* - Cambiar idioma\nℹ️ *Acerca de* - Sobre este bot",
        'help': "*Comandos Disponibles:*\n🔍 *Ver Tokens*\n📄 *Ver Transferencias*\n🌐 *Cambiar Idioma*\nℹ️ *Acerca de*",
        'choose_language': "Por favor elige tu idioma:",
        'tokens_prompt': "Envía una wallet o varias para ver tokens.",
        'transfers_prompt': "Envía una wallet para ver transferencias.",
        'wallet_invalid': "Dirección de wallet inválida.",
        'no_tokens': "No se encontraron tokens en esta wallet.",
        'no_recent_transfers': "No se encontraron transferencias recientes.",
        'balance': "*Wallet:* `{}`\n{}*Balance SOL:* `{:.4f}`\n\n",
        'recent_transfers': "Transferencias recientes de SOL, USDC y USDT:\n",
        'about': "Este bot fue creado para developers que quieran analizar wallets en Solana. Proyecto open source."
    }
}

def get_lang(chat_id):
    return user_languages.get(chat_id, 'en')

def decode_metadata(data_bytes):
    try:
        offset = 1 + 32 + 32
        name_len = struct.unpack_from("<I", data_bytes, offset)[0]
        offset += 4
        name = data_bytes[offset:offset+name_len].decode().rstrip("\x00")
        offset += name_len
        symbol_len = struct.unpack_from("<I", data_bytes, offset)[0]
        offset += 4
        symbol = data_bytes[offset:offset+symbol_len].decode().rstrip("\x00")
        return name, symbol
    except:
        return "Unknown", "UNK"

def get_onchain_metadata(mint_address):
    try:
        mint = Pubkey.from_string(mint_address)
        metadata_pda, _ = Pubkey.find_program_address([b"metadata", bytes(METADATA_PROGRAM_ID), bytes(mint)], METADATA_PROGRAM_ID)
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getAccountInfo", "params": [str(metadata_pda), {"encoding": "base64"}]}
        response = requests.post(SOLANA_RPC_URL, json=payload)
        time.sleep(0.2)
        if response.ok:
            value = response.json()["result"]["value"]
            if value:
                data = base64.b64decode(value["data"][0])
                return decode_metadata(data)
    except:
        return None
    return None

def get_token_info(mint_address):
    metadata = get_onchain_metadata(mint_address)
    if metadata:
        return metadata
    try:
        url = SOLANA_FM_API_URL.format(mint_address)
        r = requests.get(url)
        if r.ok and r.json().get("status") == "success":
            data = r.json()["data"]
            return data["tokenName"], data["tokenSymbol"]
    except:
        pass
    try:
        url = SOLSCAN_API_URL.format(mint_address)
        r = requests.get(url)
        if r.ok:
            data = r.json()
            return data["name"], data["symbol"]
    except:
        pass
    return "Unknown", "UNK"

def get_token_accounts_by_owner(wallet_address):
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
        "params": [wallet_address, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]
    }
    try:
        r = requests.post(SOLANA_RPC_URL, json=payload)
        if r.ok:
            return r.json()["result"]["value"]
    except:
        pass
    return []

def get_sol_balance(wallet_address):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [wallet_address]}
    try:
        r = requests.post(SOLANA_RPC_URL, json=payload)
        if r.ok:
            return r.json()["result"]["value"] / 1e9
    except:
        pass
    return 0

def get_recent_transfers(wallet_address, limit=10):
    transfers = []
    before = None
    while len(transfers) < limit:
        params = {"limit": 100}
        if before:
            params["before"] = before
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [wallet_address, params]}
        try:
            r = requests.post(SOLANA_RPC_URL, json=payload)
            time.sleep(0.2)
            if not r.ok:
                break
            signatures = r.json()["result"]
            if not signatures:
                break
            before = signatures[-1]["signature"]
            for sig in signatures:
                tx_payload = {"jsonrpc": "2.0", "id": 1, "method": "getTransaction", "params": [sig["signature"], {"encoding": "jsonParsed"}]}
                tx_r = requests.post(SOLANA_RPC_URL, json=tx_payload)
                time.sleep(0.2)
                if not tx_r.ok:
                    continue
                tx = tx_r.json().get("result", None)
                if not tx:
                    continue
                instructions = tx["transaction"]["message"].get("instructions", [])
                for instr in instructions:
                    parsed = instr.get("parsed", {})
                    if instr["program"] == "system" and parsed.get("type") == "transfer":
                        info = parsed.get("info", {})
                        sol = int(info.get("lamports", 0)) / 1e9
                        if sol >= 0.8:
                            transfers.append(("SOL", info.get("destination"), sol))
                    if instr["program"] == "spl-token" and parsed.get("type") == "transfer":
                        info = parsed.get("info", {})
                        mint = info.get("mint", "")
                        if mint in [USDC_MINT, USDT_MINT]:
                            amount = info["tokenAmount"]["uiAmount"]
                            if amount >= 0.8:
                                transfers.append((mint, info.get("destination"), amount))
                if len(transfers) >= limit:
                    break
        except:
            break
    return transfers[:limit]

def create_main_keyboard(chat_id):
    lang = get_lang(chat_id)
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(KeyboardButton("🔍 View Tokens" if lang == 'en' else "🔍 Ver Tokens"))
    keyboard.add(KeyboardButton("📄 View Transfers" if lang == 'en' else "📄 Ver Transferencias"))
    keyboard.add(KeyboardButton("🌐 Change Language" if lang == 'en' else "🌐 Cambiar Idioma"))
    keyboard.add(KeyboardButton("ℹ️ About" if lang == 'en' else "ℹ️ Acerca de"))
    return keyboard

def send_split_message(chat_id, text, reply_markup=None):
    if len(text) <= 4096:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        for i in range(0, len(text), 4096):
            bot.send_message(chat_id, text[i:i+4096], parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=["start"])
def handle_start(message):
    lang = get_lang(message.chat.id)
    send_split_message(message.chat.id, texts[lang]['start'], reply_markup=create_main_keyboard(message.chat.id))

@bot.message_handler(commands=["language"])
def handle_language_command(message):
    lang_keyboard = InlineKeyboardMarkup()
    lang_keyboard.add(
        InlineKeyboardButton("English", callback_data="lang:en"),
        InlineKeyboardButton("Español", callback_data="lang:es")
    )
    bot.send_message(message.chat.id, texts[get_lang(message.chat.id)]['choose_language'], reply_markup=lang_keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang:"))
def callback_set_language(call):
    lang = call.data.split(":")[1]
    user_languages[call.message.chat.id] = lang
    bot.answer_callback_query(call.id, "Language set.")
    handle_start(call.message)

# Message Handlers
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text
    lang = get_lang(message.chat.id)
    if text.startswith("🔍") or text.startswith("Ver"):
        bot.send_message(message.chat.id, texts[lang]['tokens_prompt'])
    elif text.startswith("📄") or text.startswith("Transfer"):
        bot.send_message(message.chat.id, texts[lang]['transfers_prompt'])
    elif text.startswith("🌐") or text.startswith("Cambiar"):
        handle_language_command(message)
    elif text.startswith("ℹ️") or text.startswith("Acerca"):
        bot.send_message(message.chat.id, texts[lang]['about'])
    else:
        handle_wallet_input(message)

def handle_wallet_input(message):
    wallets = []
    text = message.text.strip()
    lang = get_lang(message.chat.id)
    for line in text.splitlines():
        match = WALLET_REGEX.match(line)
        if match:
            wallets.append((match.group(1), match.group(2)))
    if not wallets:
        wallet = text
        if len(wallet) < 32 or len(wallet) > 44:
            bot.send_message(message.chat.id, texts[lang]['wallet_invalid'])
            return
        process_wallet(message.chat.id, wallet)
    else:
        for wallet, desc in wallets:
            process_wallet(message.chat.id, wallet, desc)

def process_wallet(chat_id, wallet_address, description=""):
    lang = get_lang(chat_id)
    tokens = get_token_accounts_by_owner(wallet_address)
    sol_balance = get_sol_balance(wallet_address)
    text = texts[lang]['balance'].format(wallet_address, f"_{description}_\n" if description else "", sol_balance)
    if sol_balance < 1 and not any(t['account']['data']['parsed']['info']['mint'] == USDC_MINT for t in tokens):
        transfers = get_recent_transfers(wallet_address)
        if transfers:
            text += texts[lang]['recent_transfers']
            for token, dest, amount in transfers:
                token_name = "SOL" if token == "SOL" else "USDC" if token == USDC_MINT else "USDT"
                text += f"- {token_name} to [`{dest}`](https://solscan.io/account/{dest}): {amount:.2f}\n"
        else:
            text += texts[lang]['no_recent_transfers']
    else:
        if not tokens:
            text += texts[lang]['no_tokens']
        else:
            for account in tokens:
                info = account['account']['data']['parsed']['info']
                mint = info['mint']
                amount = info['tokenAmount']['uiAmount']
                if amount > 0:
                    name, symbol = get_token_info(mint)
                    text += f"- *{name}* ({symbol}): {amount}\n"
    send_split_message(chat_id, text)

if __name__ == "__main__":
    print("Bot Started...")
    bot.polling(none_stop=True)
