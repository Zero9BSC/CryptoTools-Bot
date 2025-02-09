import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import re
import base64
import struct
import time
from solders.pubkey import Pubkey

# Configuración del bot
TOKEN = '7009028228:AAH1EgXFB1V1JqzKUXoDvzydB8lYdcEV8bI'
bot = telebot.TeleBot(TOKEN)

# URL del endpoint oficial de Solana Mainnet
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# URL de la API de Solana FM y Solscan (fallback)
SOLANA_FM_API_URL = "https://api.solana.fm/v0/tokens/{}"
SOLSCAN_API_URL = "https://api.solscan.io/token/{}"

# METADATA PROGRAM ID de Metaplex
METADATA_PROGRAM_ID = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")

# USDC mint address en Solana
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Diccionarios para almacenar el estado de cada usuario y las descripciones de las wallets
user_states = {}          # { chat_id: bool } --> si mostrar tokens con balance 0 o no
wallet_descriptions = {}  # { (chat_id, wallet_address): extra_info }

# Expresión regular para identificar wallets y descripciones
WALLET_REGEX = re.compile(r"([1-9A-HJ-NP-Za-km-z]{32,44})\s+(.+)")

def decode_metadata(data_bytes):
    try:
        offset = 0
        key = data_bytes[offset]
        offset += 1
        offset += 32 + 32  # update_authority y mint
        name_len = struct.unpack_from("<I", data_bytes, offset)[0]
        offset += 4
        name = data_bytes[offset: offset+name_len].decode("utf-8").rstrip("\x00")
        offset += name_len
        symbol_len = struct.unpack_from("<I", data_bytes, offset)[0]
        offset += 4
        symbol = data_bytes[offset: offset+symbol_len].decode("utf-8").rstrip("\x00")
        return name, symbol
    except Exception as e:
        print("Error decoding metadata:", e)
        return "Unknown", "UNK"

def get_onchain_metadata(mint_address):
    try:
        mint = Pubkey.from_string(mint_address)
        metadata_pda, _ = Pubkey.find_program_address(
            [b"metadata", bytes(METADATA_PROGRAM_ID), bytes(mint)],
            METADATA_PROGRAM_ID
        )
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [str(metadata_pda), {"encoding": "base64"}]
        }
        response = requests.post(SOLANA_RPC_URL, json=payload)
        time.sleep(0.2)
        if response.status_code == 200:
            result = response.json().get("result", {}).get("value", None)
            if result and "data" in result:
                base64_data = result["data"][0]
                data_bytes = base64.b64decode(base64_data)
                return decode_metadata(data_bytes)
        return None
    except Exception as e:
        print(f"Error al obtener metadata on-chain para {mint_address}: {e}")
        return None

def get_token_info(mint_address):
    metadata = get_onchain_metadata(mint_address)
    if metadata:
        return metadata
    try:
        url = SOLANA_FM_API_URL.format(mint_address)
        response = requests.get(url)
        time.sleep(0.2)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                name = data["data"].get("tokenName")
                symbol = data["data"].get("tokenSymbol")
                if name and symbol:
                    return name, symbol
        url = SOLSCAN_API_URL.format(mint_address)
        response = requests.get(url)
        time.sleep(0.2)
        if response.status_code == 200:
            data = response.json()
            name = data.get("name")
            symbol = data.get("symbol")
            if name and symbol:
                return name, symbol
        return "Metadata no disponible", "N/A"
    except Exception as e:
        print(f"Error al obtener información del token {mint_address}: {e}")
        return "Metadata no disponible", "N/A"

def get_token_accounts_by_owner(wallet_address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet_address,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"}
        ]
    }
    try:
        response = requests.post(SOLANA_RPC_URL, json=payload)
        time.sleep(0.2)
        if response.status_code == 200:
            data = response.json()
            return data.get("result", {}).get("value", [])
        else:
            print("Error en la llamada RPC:", response.status_code, response.text)
            return []
    except Exception as e:
        print("Excepción al llamar al RPC:", e)
        return []

def get_sol_balance(wallet_address):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address]
    }
    try:
        response = requests.post(SOLANA_RPC_URL, json=payload)
        time.sleep(0.2)
        if response.status_code == 200:
            data = response.json()
            return data.get("result", {}).get("value", 0) / 1e9
        else:
            print("Error en la llamada RPC:", response.status_code, response.text)
            return 0
    except Exception as e:
        print("Excepción al llamar al RPC:", e)
        return 0

def get_recent_transfers(wallet_address, limit=10):
    transfers = []
    before = None
    backoff = 0.5
    while len(transfers) < limit:
        params = {"limit": 100}
        if before:
            params["before"] = before
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [wallet_address, params]
        }
        try:
            response = requests.post(SOLANA_RPC_URL, json=payload)
            if response.status_code == 429:
                print("Error 429 en getSignaturesForAddress, esperando", backoff, "segundos...")
                time.sleep(backoff)
                backoff *= 2
                continue
            else:
                backoff = 0.5
            time.sleep(0.5)
            if response.status_code != 200:
                print("Error en getSignaturesForAddress:", response.status_code, response.text)
                break
            data = response.json()
            sigs = data.get("result", [])
            if not sigs:
                break
            before = sigs[-1]["signature"]
            for sig in sigs:
                tx_sig = sig["signature"]
                payload_tx = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [tx_sig, {"encoding": "jsonParsed"}]
                }
                try:
                    resp_tx = requests.post(SOLANA_RPC_URL, json=payload_tx)
                    if resp_tx.status_code == 429:
                        print("Error 429 en getTransaction, esperando", backoff, "segundos...")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    else:
                        backoff = 0.5
                    time.sleep(0.5)
                    if resp_tx.status_code != 200:
                        continue
                    tx_data = resp_tx.json().get("result", None)
                    if not tx_data:
                        continue
                    message = tx_data["transaction"]["message"]
                    instructions = message.get("instructions", [])
                    for instr in instructions:
                        if instr.get("program") == "system":
                            parsed = instr.get("parsed", {})
                            if parsed.get("type") == "transfer":
                                info = parsed.get("info", {})
                                destination = info.get("destination")
                                lamports = int(info.get("lamports", 0))
                                sol_amount = lamports / 1e9
                                if sol_amount >= 0.8:
                                    transfers.append({
                                        "type": "SOL",
                                        "destination": destination,
                                        "sol_amount": sol_amount,
                                        "signature": tx_sig
                                    })
                                    break
                        elif instr.get("program") == "spl-token":
                            parsed = instr.get("parsed", {})
                            if parsed.get("type") == "transfer":
                                info = parsed.get("info", {})
                                mint = info.get("mint", "")
                                if mint == USDC_MINT:
                                    destination = info.get("destination")
                                    amount = info.get("tokenAmount", {}).get("uiAmount", 0)
                                    if amount >= 0.8:
                                        transfers.append({
                                            "type": "USDC",
                                            "destination": destination,
                                            "amount": amount,
                                            "signature": tx_sig
                                        })
                                        break
                    if len(transfers) >= limit:
                        break
                except Exception as e:
                    print(f"Error al procesar la transacción {tx_sig}: {e}")
                    continue
        except Exception as e:
            print("Excepción en getSignaturesForAddress:", e)
            break
    return transfers[:limit]

def format_tokens_info(token_accounts, show_zero_balance=False):
    if not token_accounts:
        return "No se encontraron tokens en esta wallet."
    message = "🔍 *Tokens en la wallet:*\n"
    for account in token_accounts:
        info = account["account"]["data"]["parsed"]["info"]
        mint = info.get("mint", "N/A")
        token_amount = info.get("tokenAmount", {})
        balance = token_amount.get("uiAmount", 0)
        if not show_zero_balance and balance == 0:
            continue
        token_name, token_symbol = get_token_info(mint)
        message += f"- *{token_name}* ({token_symbol}): {balance}\n"
    return message

def create_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(KeyboardButton("🔍 Ver Tokens"))
    keyboard.add(KeyboardButton("📄 Ver Transacciones"), KeyboardButton("❓ Ayuda"))
    return keyboard

@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_message = (
        "¡Bienvenido al *bot de Solana*! 🚀\n\n"
        "Comandos:\n"
        "🔍 *Ver Tokens* - Ver los tokens de una wallet\n"
        "📄 *Ver Transacciones* - Ver las últimas transacciones de una wallet\n"
        "❓ *Ayuda* - Obtener ayuda"
    )
    bot.send_message(message.chat.id, welcome_message, parse_mode="Markdown", reply_markup=create_keyboard(), disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text == "🔍 Ver Tokens")
def handle_tokens_button(message):
    bot.send_message(message.chat.id, "Envía la dirección de la wallet o un listado de wallets para ver los tokens.", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text == "📄 Ver Transacciones")
def handle_transactions_button(message):
    bot.send_message(message.chat.id, "Envía la dirección de la wallet para ver las transacciones.", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text == "❓ Ayuda")
def handle_help_button(message):
    help_message = (
        "*Comandos disponibles:*\n"
        "🔍 *Ver Tokens* - Ver los tokens de una wallet\n"
        "📄 *Ver Transacciones* - Ver las últimas transacciones de una wallet\n"
        "❓ *Ayuda* - Obtener ayuda"
    )
    bot.send_message(message.chat.id, help_message, parse_mode="Markdown", reply_markup=create_keyboard(), disable_web_page_preview=True)

@bot.message_handler(func=lambda message: True)
def handle_wallet_address_input(message):
    text = message.text.strip()
    wallets = []
    for line in text.splitlines():
        match = WALLET_REGEX.match(line)
        if match:
            wallet_address, description = match.groups()
            wallets.append((wallet_address, description))
    if not wallets:
        wallet_address = text
        if len(wallet_address) < 32 or len(wallet_address) > 44:
            bot.send_message(message.chat.id, "La dirección de la wallet no es válida.", disable_web_page_preview=True)
            return
        process_wallet(message.chat.id, wallet_address, extra_info="")
    else:
        for wallet_address, description in wallets:
            process_wallet(message.chat.id, wallet_address, extra_info=f"Descripción: {description}\n")

def process_wallet(chat_id, wallet_address, extra_info=""):
    token_accounts = get_token_accounts_by_owner(wallet_address)
    sol_balance = get_sol_balance(wallet_address)
    wallet_descriptions[(chat_id, wallet_address)] = extra_info
    has_sol = sol_balance >= 1  # Considera que "tiene SOL" solo si es >= 1
    has_usdc = any(
        account["account"]["data"]["parsed"]["info"].get("mint", "") == USDC_MINT and
        account["account"]["data"]["parsed"]["info"].get("tokenAmount", {}).get("uiAmount", 0) > 0
        for account in token_accounts
    )
    if not has_sol and not has_usdc:
        transfers = get_recent_transfers(wallet_address, limit=10)
        response = f"*Wallet:* `{wallet_address}`\n" \
                   f"{extra_info}" \
                   f"*Balance de SOL:* {sol_balance:.4f}\n\n" \
                   "La wallet no tiene SOL (balance < 1) ni USDC. Últimas transferencias de SOL/USDC:\n"
        if transfers:
            for t in transfers:
                if t["type"] == "SOL":
                    # Mostrar con 2 decimales en SOL
                    response += f"- SOL transferido a: [`{t['destination']}`](https://solscan.io/account/{t['destination']}) (Monto: {t['sol_amount']:.2f} SOL)\n"
                elif t["type"] == "USDC":
                    response += f"- USDC transferido a: [`{t['destination']}`](https://solscan.io/account/{t['destination']}) (Monto: {t['amount']:.2f} USDC)\n"
        else:
            response += "No se encontraron transferencias recientes."
        bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        show_zero_balance = user_states.get(chat_id, False)
        response = f"*Wallet:* `{wallet_address}`\n" \
                   f"{extra_info}" \
                   f"*Balance de SOL:* {sol_balance:.4f}\n\n" \
                   + format_tokens_info(token_accounts, show_zero_balance)
        has_zero_balance = any(
            account["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmount", 0) == 0
            for account in token_accounts
        )
        keyboard = None
        if has_zero_balance:
            keyboard = InlineKeyboardMarkup()
            if show_zero_balance:
                keyboard.add(InlineKeyboardButton("Ocultar tokens con balance 0", callback_data=f"toggle:{wallet_address}"))
            else:
                keyboard.add(InlineKeyboardButton("Mostrar tokens con balance 0", callback_data=f"toggle:{wallet_address}"))
        bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle:"))
def handle_callback(call):
    chat_id = call.message.chat.id
    wallet_address = call.data.split("toggle:")[1].strip()
    extra_info = wallet_descriptions.get((chat_id, wallet_address), "")
    current_state = user_states.get(chat_id, False)
    user_states[chat_id] = not current_state
    token_accounts = get_token_accounts_by_owner(wallet_address)
    sol_balance = get_sol_balance(wallet_address)
    show_zero_balance = user_states.get(chat_id, False)
    response = f"*Wallet:* `{wallet_address}`\n" \
               f"{extra_info}" \
               f"*Balance de SOL:* {sol_balance:.4f}\n\n" \
               + format_tokens_info(token_accounts, show_zero_balance)
    has_zero_balance = any(
        account["account"]["data"]["parsed"]["info"]["tokenAmount"].get("uiAmount", 0) == 0
        for account in token_accounts
    )
    keyboard = None
    if has_zero_balance:
        keyboard = InlineKeyboardMarkup()
        if show_zero_balance:
            keyboard.add(InlineKeyboardButton("Ocultar tokens con balance 0", callback_data=f"toggle:{wallet_address}"))
        else:
            keyboard.add(InlineKeyboardButton("Mostrar tokens con balance 0", callback_data=f"toggle:{wallet_address}"))
    try:
        bot.edit_message_text(response, chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        print(f"Error al editar el mensaje: {e}")

if __name__ == "__main__":
    print("Bot iniciado...")
    bot.polling(none_stop=True)
