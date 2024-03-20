import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7009028228:AAH1EgXFB1V1JqzKUXoDvzydB8lYdcEV8bI'
bot = telebot.TeleBot(TOKEN)

contract_input = {}
# Diccionario para almacenar la private key de cada usuario
private_keys = {}

# Función para enviar el mensaje de bienvenida con el menú
def send_welcome_message(chat_id):
    welcome_message = "¡Bienvenido a mi bot de Telegram!\n\n"
    welcome_message += "Puedes usar los siguientes comandos:\n"
    welcome_message += "/trader - Solicitar el contrato de un token\n"
    welcome_message += "/add_wallet - Agregar tu wallet de Solana\n"
    welcome_message += "/help - Obtener ayuda y ver los comandos disponibles\n"
    
    # Creamos los botones del menú
    menu_markup = InlineKeyboardMarkup()
    menu_markup.row_width = 2  # Dos botones por fila

    # Botón Add Wallet con el emoticon +
    add_wallet_icon = u'\U00002795'  # Icono de cruz en cuadrado
    menu_markup.add(InlineKeyboardButton(f'{add_wallet_icon} Add Wallet', callback_data='add_wallet'))

    # Botón Buy & Sell y Token Sniper
    buy_icon = u'\U0001F4B0'  # Icono de moneda
    sniper_icon = u'\U0001F3F9'  # Icono de objetivo
    menu_markup.add(InlineKeyboardButton(f'{buy_icon} Buy & Sell', callback_data='buy_tokens'),
                    InlineKeyboardButton(f'{sniper_icon} Token Sniper', callback_data='tokens_sniper'))

    # Botones Profile, Wallets y Trades
    profile_icon = u'\U0001F464'  # Icono de persona
    wallets_icon = u'\U0001F4B3'  # Icono de cartera
    trades_icon = u'\U0001F4C8'  # Icono de gráfico
    menu_markup.add(InlineKeyboardButton(f'{profile_icon} Profile', callback_data='profile'),
                    InlineKeyboardButton(f'{wallets_icon} Wallets', callback_data='wallets'),
                    InlineKeyboardButton(f'{trades_icon} Trades', callback_data='trades'))
    
    bot.send_message(chat_id, welcome_message, reply_markup=menu_markup)

@bot.message_handler(commands=['start'])
def handle_start(message):
    send_welcome_message(message.chat.id)

@bot.message_handler(commands=['help'])
def handle_help(message):
    send_welcome_message(message.chat.id)

@bot.message_handler(commands=['add_wallet'])
def add_wallet(message):
    # Verificamos si ya tenemos la private key del usuario
    if message.chat.id in private_keys:
        bot.send_message(message.chat.id, "Ya has agregado tu wallet anteriormente.")
    else:
        bot.send_message(message.chat.id, "Por favor, ingresa tu clave privada de la wallet de Solana.")

@bot.message_handler(func=lambda message: True)
def handle_private_key(message):
    # Verificamos si ya tenemos la private key del usuario
    if message.chat.id in private_keys:
        bot.send_message(message.chat.id, "Ya has agregado tu wallet anteriormente.")
        return
    
    private_key = message.text
    user_id = message.chat.id
    private_keys[user_id] = private_key
    bot.send_message(user_id, "¡Tu wallet de Solana ha sido agregada con éxito!")
    send_welcome_message(user_id)  # Enviamos el mensaje de bienvenida nuevamente

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.data == 'buy_tokens':
        bot.send_message(chat_id, 'Has seleccionado Buy & Sell.')
    elif call.data == 'tokens_sniper':
        bot.send_message(chat_id, 'Has seleccionado Token Sniper.')
    elif call.data == 'profile':
        bot.send_message(chat_id, 'Has seleccionado Profile.')
    elif call.data == 'wallets':
        bot.send_message(chat_id, 'Tu wallet de Solana: {}'.format(private_keys.get(chat_id, "No has agregado tu wallet aún.")))
    elif call.data == 'trades':
        bot.send_message(chat_id, 'Has seleccionado Trades.')
    elif call.data == 'add_wallet':
        add_wallet(call.message)

if __name__ == "__main__":
    bot.polling(none_stop=True)