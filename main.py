import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from solana.rpc.api import Client
from solders.pubkey import Pubkey

TOKEN = '7009028228:AAH1EgXFB1V1JqzKUXoDvzydB8lYdcEV8bI'
bot = telebot.TeleBot(TOKEN)

# Diccionario para almacenar la private key de cada usuario
private_keys = {}
# URL del nodo de Solana (mainnet)
SOLANA_NODE_URL = "https://api.mainnet-beta.solana.com"

# Función para enviar el mensaje de bienvenida con el menú
def send_welcome_message(chat_id):
    welcome_message = "¡Bienvenido a mi bot de Telegram!\n\n"
    welcome_message += "Puedes usar los siguientes comandos:\n"
    welcome_message += "/trader - Solicitar el contrato de un token\n"
    welcome_message += "/add_wallet - Agregar tu wallet de Solana\n"
    welcome_message += "/help - Obtener ayuda y ver los comandos disponibles\n"

    bot.send_message(chat_id, welcome_message)

# Función para obtener la información de la cuenta de Solana
def get_solana_account_info(public_key):
    solana_client = Client(SOLANA_NODE_URL)
    return solana_client.get_account_info(Pubkey(public_key))

# Función para obtener el saldo de Solana
def get_solana_balance(public_key):
    solana_client = Client(SOLANA_NODE_URL)
    return solana_client.get_balance(Pubkey(public_key))

# Función para agregar la wallet de Solana
def add_wallet(chat_id, message_text):
    # Verificamos si ya tenemos la private key del usuario
    if chat_id in private_keys:
        bot.send_message(chat_id, "Ya has agregado tu wallet anteriormente.")
        return
    
    private_key = message_text
    private_keys[chat_id] = private_key
    bot.send_message(chat_id, "¡Tu wallet de Solana ha sido agregada con éxito!")
    send_welcome_message(chat_id)  # Enviamos el mensaje de bienvenida nuevamente

@bot.message_handler(commands=['start'])
def handle_start(message):
    send_welcome_message(message.chat.id)

@bot.message_handler(commands=['help'])
def handle_help(message):
    send_welcome_message(message.chat.id)

@bot.message_handler(commands=['add_wallet'])
def add_wallet_command(message):
    bot.send_message(message.chat.id, "Por favor, ingresa tu clave privada de la wallet de Solana.")

@bot.message_handler(func=lambda message: True)
def handle_private_key(message):
    add_wallet(message.chat.id, message.text)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.data == 'buy_tokens':
        bot.send_message(chat_id, 'Has seleccionado Buy & Sell.')
    elif call.data == 'tokens_sniper':
        bot.send_message(chat_id, 'Has seleccionado Token Sniper.')
    elif call.data == 'profile':
        # Obtenemos la información de la cuenta y el saldo
        public_key = private_keys.get(chat_id)
        account_info = get_solana_account_info(public_key)
        balance = get_solana_balance(public_key)

        # Construimos el mensaje de perfil
        profile_message = "🔍 Perfil\n\n"
        profile_message += f"Your Wallet\n"
        profile_message += f"Dirección de la wallet: {public_key}\n"
        profile_message += f"Balance: {balance} SOL\n\n"
        profile_message += f"View on Explorer: [Ver en Solana Explorer](https://solscan.io/account/{public_key})"

        bot.send_message(chat_id, profile_message, parse_mode='Markdown', disable_web_page_preview=True)
    elif call.data == 'wallets':
        bot.send_message(chat_id, 'Tu wallet de Solana: {}'.format(private_keys.get(chat_id, "No has agregado tu wallet aún.")))
    elif call.data == 'trades':
        bot.send_message(chat_id, 'Has seleccionado Trades.')
    elif call.data == 'add_wallet':
        add_wallet_command(call.message)

if __name__ == "__main__":
    bot.polling(none_stop=True)