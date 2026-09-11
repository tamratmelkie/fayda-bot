import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# Configuration from Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")

# Conversation States
ENTER_FIN, CONFIRM_PAYMENT, ENTER_OTP = range(3)

# Fayda Portal URLs (Placeholder endpoints for Fayda HTTP automation)
FAYDA_BASE_URL = "https://id.gov.et" 

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

    keyboard = [[InlineKeyboardButton("✅ ክፍያውን አረጋግጥ (Demo)", callback_data="pay_demo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📌 FIN ቁጥር: {fin_number}\n"
        f"💵 የአገልግሎት ክፍያ: 20 ብር\n\n"
        f"እባክዎን ከታች ያለውን 'ክፍያውን አረጋግጥ' የሚለውን ይጫኑ፦",
        reply_markup=reply_markup
    )
    return CONFIRM_PAYMENT

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    fin = context.user_data.get('fin')
    await query.edit_message_text(text="⏳ ክፍያዎ ተረጋግጧል! ወደ ፋይዳ ፖርታል የ OTP ጥያቄ እየተላከ ነው...")

    # Step 2: Trigger OTP to user's phone via Fayda Session
    session = requests.Session()
    context.user_data['session'] = session
    
    # Simulating sending FIN to Fayda portal to request OTP
    # try:
    #     res = session.post(f"{FAYDA_BASE_URL}/api/request-otp", json={"fin": fin})
    # except Exception as e:
    #     pass

    await query.message.reply_text(
        "📲 በፋይዳ የተመዘገበው ስልክዎ ላይ የ 6 ዲጂት OTP ኮድ ተልኳል።\n\n"
        "እባክዎን የደረሰዎትን OTP ኮድ እዚህ ይጻፉልኝ፦"
    )
    return ENTER_OTP

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin = context.user_data.get('fin')

    await update.message.reply_text("🔄 OTP እየተረጋገጠ ነው... እባክዎን ትንሽ ይጠብቁ።")

    # Step 3: Verify OTP and fetch PDF from Fayda portal
    # session = context.user_data.get('session')
    # pdf_response = session.post(f"{FAYDA_BASE_URL}/api/verify-otp", json={"fin": fin, "otp": otp_code})

    # Dummy PDF creation for testing flow (Replace with actual pdf download bytes)
    pdf_path = f"{fin}_fayda.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 ... Fayda ID Document Content ...")

    # Send Document to User on Telegram
    with open(pdf_path, "rb") as pdf_file:
        await update.message.reply_document(
            document=pdf_file,
            filename=f"Fayda_ID_{fin}.pdf",
            caption="✅ የፋይዳ PDF መታወቂያዎ በተሳካ ሁኔታ ተወርዷል!"
        )

    # Clean up local temporary file
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
            CONFIRM_PAYMENT: [CallbackQueryHandler(handle_payment, pattern="^pay_demo$")],
            ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()    app.add_handler(conv_handler)
    print("🤖 ቦቱ በRender ሰርቨር ላይ ለመነሳት ዝግጁ ነው...")
    app.run_polling()
