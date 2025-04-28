# Solana Wallet Bot 🤖

A Telegram bot built for developers to quickly **analyze Solana wallets**.

✅ Check SOL balance  
✅ View SPL tokens (with token names and symbols)  
✅ Filter tokens with 0 balance  
✅ Display recent SOL, USDC, and USDT transfers  
✅ Multi-language support: **English** and **Spanish**  
✅ Free: uses **public Solana RPC**, no API keys required

---

## Features ✨

- **Token Overview:**  
  View all SPL tokens associated with a wallet, with readable names and symbols.

- **Balance Information:**  
  Show the SOL balance of the wallet with 4 decimal places.

- **Recent Transfers:**  
  If the wallet has less than 1 SOL or no USDC/USDT, the bot shows the last SOL, USDC, and USDT transfers.

- **Language Support:**  
  The user can switch between English and Spanish anytime using `/language`.

- **Multiple Wallet Input:**  
  You can send multiple wallet addresses at once (one per line).

- **Inline Options:**  
  Toggle visibility of tokens with 0 balance directly from the chat.

- **Public Solana RPC:**  
  No signup, API key, or payment required. Works with the official Solana RPC endpoint.

---

## Commands 📜

- `/start` — Show welcome message and options.
- `/help` — Display available commands and instructions.
- `/language` — Switch between English and Spanish.
- `/about` — Learn more about the bot.

---

## How to Use ⚡

1. Start the bot using `/start`.
2. Use the buttons to select:
   - 🔍 View Tokens
   - 📄 View Transactions
   - 🌐 Change Language
3. Send a wallet address (or multiple addresses, one per line).
4. Instantly receive SOL balance, token holdings, or recent transaction history!

---

## Technologies 🛠️

- **Python 3.12**
- **PyTelegramBotAPI** (Telebot)
- **Requests** (HTTP library)
- **Solders** (for Pubkey generation)
- **Solana Official RPC API**

---

## Installation 📦

Install the required packages:

```bash
pip install -r requirements.txt
```

Clone the project and run:

```bash
python main.py
```

---

## Requirements 🔧

- Python 3.10 or newer
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

---

## Contributing 🤝

Pull requests are welcome!  
If you find bugs or have ideas for improvement, feel free to open an issue.

---

## License 📄

This project is open-source and licensed under the MIT License.

---

## About 📣

This bot was developed for developers and crypto enthusiasts to quickly analyze Solana wallets without the need for complicated tools.  
Built with ❤️ using Python and the public Solana API.

# 🚀 Let's make Solana wallet tracking easier together!

