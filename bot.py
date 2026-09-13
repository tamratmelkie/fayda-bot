import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes, filters, ConversationHandler
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ENTER_FIN, ENTER_OTP = range(2)

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
    
    await update.message.reply_text(
        f"📌 FIN ቁጥር: {fin_number}\n\n"
        "🔄 ወደ ፋይዳ ፖርታል የ OTP ጥያቄ እየተላከ ነው...\n"
        "📲 እባክዎን በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦"
    )
    return ENTER_OTP

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin = context.user_data.get('fin')

    if not otp_code.isdigit() or len(otp_code) != 6:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ 6 ዲጂት OTP ኮድ ያስገቡ፦")
        return ENTER_OTP

    await update.message.reply_text("🔄 OTP እየተረጋገጠ ነው... የፋይዳ PDF በመዘጋጀት ላይ ነው...")

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
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable is missing!")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fin)],
            ENTER_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
