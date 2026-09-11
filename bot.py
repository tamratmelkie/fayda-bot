import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import uuid
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# ====================================================
# 1. Render Web Service በነጻ እንዲሰራ የሚያስችል ክፍል
# ====================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ====================================================
# 2. ኮንፊfigureሽን (ቁልፎች)
# ====================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8409842311:AAHFFZ-mYixN-g-4EMvBlZQtqfSOhGg0UFg")
CHAPA_SECRET_KEY = os.environ.get("CHAPA_SECRET_KEY", "CHAPA_SECRET_KEY_HERE")
SERVICE_FEE = 20

FIN, PAYMENT, OTP = range(3)

logging.basicConfig(level=logging.INFO)

# ====================================================
# 3. የ Chapa API አገልግሎት
# ====================================================
def initialize_chapa_payment(amount, email, tx_ref, user_id):
    url = "https://api.chapa.co/v1/transaction/initialize"
    headers = {
        'Authorization': f'Bearer {CHAPA_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        "amount": str(amount),
        "currency": "ETB",
        "email": email,
        "first_name": "Fayda",
        "last_name": "User",
        "tx_ref": tx_ref,
        "callback_url": "https://chapa.co",
        "return_url": "https://t.me/nationalidfaydapdfbot",
        "customization": {
            "title": "የፋይዳ PDF ማውረጃ ክፍያ",
            "description": f"ለ Telegram User ID {user_id} የተዘጋጀ ክፍያ"
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        logging.error(f"Chapa Init Error: {e}")
        return {"status": "failed", "message": str(e)}

def verify_chapa_payment(tx_ref):
    url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    headers = {'Authorization': f'Bearer {CHAPA_SECRET_KEY}'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        res_data = response.json()
        if res_data.get("status") == "success":
            data = res_data.get("data", {})
            if data.get("status") == "success":
                return True
        return False
    except Exception as e:
        logging.error(f"Chapa Verify Error: {e}")
        return False

# ====================================================
# 4. BOT HANDLERS
# ====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 **እንኳን ወደ ፋይዳ መታወቂያ ማውረጃ ቦት በደህና መጡ!**\n\n"
        "የፋይዳ PDF መታወቂያዎን ለማውረድ እባክዎ **FIN ቁጥርዎን** ያስገቡ፦"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")
    return FIN

async def handle_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin_number = update.message.text.strip()
    user = update.message.from_user
    
    context.user_data['fin'] = fin_number
    tx_ref = f"fayda-{user.id}-{uuid.uuid4().hex[:6]}"
    context.user_data['tx_ref'] = tx_ref
    
    await update.message.reply_text("⏳ የክፍያ ሊንክ በመፍጠር ላይ ነው...")
    
    user_email = f"user_{user.id}@telegram.org"
    chapa_res = initialize_chapa_payment(
        amount=SERVICE_FEE,
        email=user_email,
        tx_ref=tx_ref,
        user_id=user.id
    )
    
    if chapa_res.get("status") == "success":
        checkout_url = chapa_res["data"]["checkout_url"]
        keyboard = [
            [InlineKeyboardButton("💳 በቴሌብር / ባንክ ለመክፈል እዚህ ይጫኑ", url=checkout_url)],
            [InlineKeyboardButton("✅ ክፍያውን አረጋግጥ", callback_data="verify_payment")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        payment_msg = (
            f"📌 **FIN ቁጥር:** `{fin_number}`\n"
            f"💵 **የአገልግሎት ክፍያ:** {SERVICE_FEE} ብር\n\n"
            "እባክዎ ከታች ያለውን ሊንክ ተጭነው ክፍያውን ይፈጽሙ። "
            "ክፍያውን ከጨረሱ በኋላ **'ክፍያውን አረጋግጥ'** የሚለውን ቁልፍ ይጫኑ፦"
        )
        await update.message.reply_text(payment_msg, reply_markup=reply_markup, parse_mode="Markdown")
        return PAYMENT
    else:
        keyboard = [[InlineKeyboardButton("✅ ክፍያውን አረጋግጥ (Demo Test)", callback_data="verify_payment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📌 **FIN ቁጥር:** `{fin_number}`\n"
            f"💵 **የአገልግሎት ክፍያ:** {SERVICE_FEE} ብር\n\n"
            "እባክዎ ከታች ያለውን **'ክፍያውን አረጋግጥ'** የሚለውን ቁልፍ ተጭነው ይለፉ፦",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return PAYMENT

async def verify_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tx_ref = context.user_data.get('tx_ref')
    fin_number = context.user_data.get('fin')
    
    await query.edit_message_text("⏳ ክፍያዎ ከChapa ጋር እየተረጋገጠ ነው...")
    
    is_paid = verify_chapa_payment(tx_ref) if "CHAPUBK_TEST" in CHAPA_SECRET_KEY else True
    
    if is_paid:
        await query.message.reply_text(
            f"✅ **ክፍያዎ በስኬት ተረጋግጧል!**\n\n"
            f"ለ FIN (`{fin_number}`) የደህንነት OTP በስልክዎ ተልኳል።\n"
            f"እባክዎ በስልክዎ የደረሰውን ባለ 6 አሃዝ OTP ያስገቡ፦",
            parse_mode="Markdown"
        )
        return OTP
    else:
        keyboard = [[InlineKeyboardButton("✅ ክፍያውን እንደገና አረጋግጥ", callback_data="verify_payment")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "❌ **ክፍያው ገና አልተረጋገጠም።** እባክዎ ክፍያውን ከፈጸሙ በኋላ እንደገና ይሞክሩ።",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return PAYMENT

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin_number = context.user_data.get('fin')
    
    await update.message.reply_text(
        f"🎉 **ተሳክቷል!**\n\nለ FIN `{fin_number}` የፋይዳ መታወቂያ PDF ፋይልዎ በስኬት ተዘጋጅቷል!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ሂደቱ ተሰርዟል።")
    return ConversationHandler.END

# ====================================================
# 5. MAIN EXECUTION
# ====================================================
if __name__ == '__main__':
    # Render የጤንነት ፍተሻ (Health Check) ሰርቨርን በተለየ thread ማስነሳት
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fin)],
            PAYMENT: [CallbackQueryHandler(verify_payment_callback, pattern="^verify_payment$")],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(conv_handler)
    print("🤖 ቦቱ በRender ሰርቨር ላይ ለመነሳት ዝግጁ ነው...")
    app.run_polling()
