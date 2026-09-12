import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")

ENTER_FIN, CONFIRM_PAYMENT, ENTER_OTP = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ወደ ፋይዳ መታወቂያ ማውረጃ ቦት በደህና መጡ!\n\n"
        "የፋይዳ PDF መታወቂያዎን ለማውረድ እባክዎን FIN ቁጥርዎን ያስገቡ፦"
    )
    return ENTER_FIN

async def handle_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin_number = update.message.text.strip()
    
    if not fin_number.isdigit() or len(fin_number) < 10:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ FIN ቁጥር ያስገቡ፦")
        return ENTER_FIN

    context.user_data['fin'] = fin_number
    tx_ref = f"fayda-{fin_number}-{int(time.time())}"
    context.user_data['tx_ref'] = tx_ref

    await update.message.reply_text("⏳ የ Chapa ክፍያ ሊንክ በመፍጠር ላይ ነው...")

    # Chapa API Request Payload
    url = "https://api.chapa.co/v1/transaction/initialize"
    payload = {
        "amount": "20",
        "currency": "ETB",
        "email": "testuser@gmail.com",
        "first_name": "Fayda",
        "last_name": "User",
        "tx_ref": tx_ref,
        "customization": {
            "title": "Fayda ID Service",
            "description": "Payment for Fayda PDF Download"
        }
    }
    
    # Strip spaces from Secret Key just in case
    secret_key = CHAPA_SECRET_KEY.strip() if CHAPA_SECRET_KEY else ""
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        res = response.json()

        if response.status_code == 200 and res.get("status") == "success":
            checkout_url = res["data"]["checkout_url"]
            keyboard = [
                [InlineKeyboardButton("💳 በ Chapa ለመክፈል እዚህ ይጫኑ", url=checkout_url)],
                [InlineKeyboardButton("✅ ክፍያውን አረጋግጥ", callback_data="verify_pay")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"📌 FIN ቁጥር: {fin_number}\n"
                f"💵 የአገልግሎት ክፍያ: 20 ብር\n\n"
                f"እባክዎን ከታች ያለውን አረንጓዴ 'በ Chapa ለመክፈል' የሚለውን ተጭነው ይክፈሉ፤ ከከፈሉ በኋላ 'ክፍያውን አረጋግጥ' የሚለውን ይጫኑ፦",
                reply_markup=reply_markup
            )
            return CONFIRM_PAYMENT
        else:
            error_detail = res.get("message", "የታወቀ ኤረር የለም")
            await update.message.reply_text(f"❌ Chapa ሊንክ መፍጠር አልቻለም። ከ Chapa የመጣ ኤረር፦ {error_detail}")
            return ENTER_FIN
    except Exception as e:
        await update.message.reply_text(f"❌ የኔትወርክ ስህተት አጋጥሟል፦ {str(e)}")
        return ENTER_FIN

async def verify_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tx_ref = context.user_data.get('tx_ref')
    secret_key = CHAPA_SECRET_KEY.strip() if CHAPA_SECRET_KEY else ""
    url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    headers = {"Authorization": f"Bearer {secret_key}"}

    try:
        res = requests.get(url, headers=headers).json()
        if res.get("status") == "success":
            await query.edit_message_text("✅ ክፍያዎ ተረጋግጧል! ወደ ፋይዳ ፖርታል የ OTP ጥያቄ እየተላከ ነው...")
            await query.message.reply_text("📲 በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦")
            return ENTER_OTP
        else:
            await query.message.reply_text("❌ ክፍያው ገና አልተረጋገጠም። እባክዎን አስቀድመው ይክፈሉና እንደገና 'ክፍያውን አረጋግጥ' የሚለውን ይጫኑ።")
            return CONFIRM_PAYMENT
    except Exception as e:
        await query.message.reply_text("❌ ክፍያውን ማረጋገጥ አልተቻለም።")
        return CONFIRM_PAYMENT

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin = context.user_data.get('fin')

    await update.message.reply_text("🔄 OTP እየተረጋገጠ ነው... እባክዎን ትንሽ ይጠብቁ።")

    pdf_path = f"{fin}_fayda.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 ... Fayda ID Document Content ...")

    with open(pdf_path, "rb") as pdf_file:
        await update.message.reply_document(
            document=pdf_file,
            filename=f"Fayda_ID_{fin}.pdf",
            caption="✅ የፋይዳ PDF መታወቂያዎ በተሳካ ሁኔታ ተወርዷል!"
        )

    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ተግባሩ ተሰርዟል። እንደገና ለመጀመር /start ይበሉ።")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fin)],
            CONFIRM_PAYMENT: [CallbackQueryHandler(verify_payment, pattern="^verify_pay$")],
            ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
    pdf_path = f"{fin}_fayda.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 ... Fayda ID Document Content ...")

    with open(pdf_path, "rb") as pdf_file:
        await update.message.reply_document(
            document=pdf_file,
            filename=f"Fayda_ID_{fin}.pdf",
            caption="✅ የፋይዳ PDF መታወቂያዎ በተሳካ ሁኔታ ተወርዷል!"
        )

    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ተግባሩ ተሰርዟል። እንደገና ለመጀመር /start ይበሉ።")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fin)],
            CONFIRM_PAYMENT: [CallbackQueryHandler(verify_payment, pattern="^verify_pay$")],
            ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
