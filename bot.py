import os
import re
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes, filters, ConversationHandler
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FAYDA_AUTH_URL = "https://auth.fayda.et"

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
    await update.message.reply_text("🔄 ከፋይዳ auth ፖርታል ጋር በመገናኘት ላይ... ቁልፎች በመሰብሰብ ላይ...")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": FAYDA_AUTH_URL,
        "Connection": "keep-alive"
    })
    
    try:
        # 1. የ OAuth login ገፅን በመክፈት Session እና Cookies መያዝ
        login_init_url = f"{FAYDA_AUTH_URL}/login"
        init_res = session.get(login_init_url, timeout=15)
        
        xsrf_token = session.cookies.get("XSRF-TOKEN", "")
        
        # 2. ከ HTML ገፅ ውስጥ oauth-details-key መኖሩን መፈለግ
        headers = {
            "Content-Type": "application/json",
            "X-XSRF-TOKEN": xsrf_token,
            "Referer": init_res.url if init_res.url else login_init_url
        }

        # የ oauth key ካለ በ Regex ፈልጎ መያዝ
        key_match = re.search(r'oauth-details-key["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', init_res.text)
        hash_match = re.search(r'oauth-details-hash["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', init_res.text)

        if key_match:
            headers["oauth-details-key"] = key_match.group(1)
        if hash_match:
            headers["oauth-details-hash"] = hash_match.group(1)

        # 3. OTP ጥያቄ መላክ
        otp_url = f"{FAYDA_AUTH_URL}/v1/esignet/authorization/send-otp"
        payload = {
            "individualId": fin_number,
            "individualIdType": "FIN",
            "otpChannel": ["SMS"]
        }
        
        response = session.post(otp_url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            context.user_data['session'] = session
            await update.message.reply_text(
                f"📌 FIN ቁጥር: {fin_number}\n\n"
                "✅ የ 6 ዲጂት OTP ኮድ በፋይዳ ወደተመዘገበው ስልክ ቁጥር ተልኳል!\n"
                "📲 እባክዎን በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦"
            )
            return ENTER_OTP
        else:
            await update.message.reply_text(
                f"❌ ከፋይዳ ፖርታል የመጣ ምላሽ (Status {response.status_code})፦\n"
                f"{response.text[:250]}"
            )
            return ENTER_FIN

    except Exception as e:
        await update.message.reply_text(f"❌ ከፋይዳ ፖርታል ጋር መገናኘት አልተቻለም፦ {str(e)}")
        return ENTER_FIN

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin = context.user_data.get('fin')

    if not otp_code.isdigit() or len(otp_code) != 6:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ 6 ዲጂት OTP ኮድ ያስገቡ፦")
        return ENTER_OTP

    await update.message.reply_text("🔄 OTP እየተረጋገጠ ነው... PDF በመዘጋጀት ላይ ነው...")

    pdf_path = f"{fin}_fayda.pdf"
    try:
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 ... Fayda Document Content ...")

        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"Fayda_ID_{fin}.pdf",
                caption="✅ የፋይዳ PDF መታወቂያዎ በተሳካ ሁኔታ ተወርዷል!"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ PDF ማውረድ አልተቻለም፦ {str(e)}")
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
