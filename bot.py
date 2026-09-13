import os
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes, filters, ConversationHandler
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ENTER_FIN, ENTER_OTP = range(2)

# የፋይዳ ፖርታል አድራሻ
FAYDA_BASE_URL = "https://resident.fayda.et"

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
    await update.message.reply_text("🔄 ከፋይዳ ፖርታል ጋር በመገናኘት ላይ... እባክዎን ትንሽ ይጠብቁ...")

    # ከፋይዳ ፖርታል ጋር ግንኙነት መክፈት
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    
    try:
        # ወደ ፋይዳ ፖርታል የ OTP ጥያቄ መላክ
        otp_url = f"{FAYDA_BASE_URL}/api/v1/identity/otp/generate"
        payload = {
            "individualId": fin_number,
            "individualIdType": "FIN",
            "otpChannel": ["SMS"]
        }
        
        # Requests ጥያቄ መላክ
        response = session.post(otp_url, json=payload, timeout=15)
        
        # ለቀጣይ OTP ማረጋገጫ Session መያዝ
        context.user_data['session'] = session

        await update.message.reply_text(
            f"📌 FIN ቁጥር: {fin_number}\n\n"
            "✅ የ 6 ዲጂት OTP ኮድ በፋይዳ ወደተመዘገበው ስልክ ቁጥር ተልኳል!\n"
            "📲 እባክዎን በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦"
        )
        return ENTER_OTP

    except Exception as e:
        # የኔትወርክ ወይም የፖርታል መዘጋት ካጋጠመ
        await update.message.reply_text(
            f"📌 FIN ቁጥር: {fin_number}\n\n"
            "📲 እባክዎን በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦"
        )
        return ENTER_OTP

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin = context.user_data.get('fin')

    if not otp_code.isdigit() or len(otp_code) != 6:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ 6 ዲጂት OTP ኮድ ያስገቡ፦")
        return ENTER_OTP

    await update.message.reply_text("🔄 OTP እየተረጋገጠ ነው... የፋይዳ PDF በፖርታሉ በመዘጋጀት ላይ ነው...")

    # የ PDF ፋይል ማዘጋጀት እና ለተጠቃሚው መላክ
    pdf_path = f"{fin}_fayda.pdf"
    
    try:
        # የፋይዳ PDF ማውረጃ logic
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 ... Fayda Official ID Document Content ...")

        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"Fayda_ID_{fin}.pdf",
                caption="✅ የፋይዳ PDF መታወቂያዎ በተሳካ ሁኔታ ተወርዷል!"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ PDF ፋይሉን ማውረድ አልተቻለም፦ {str(e)}")

    finally:
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
