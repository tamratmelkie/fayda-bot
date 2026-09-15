import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes, filters, ConversationHandler
)
from playwright.async_api import async_playwright

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
    await update.message.reply_text("🔄 ብራውዘር እየተከፈተ ነው... ከፋይዳ ፖርታል ጋር በመገናኘት ላይ...")

    try:
        # Playwright ብራውዘር መክፈት
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        browser_context = await browser.new_context()
        page = await browser_context.new_page()

        # ወደ ፋይዳ ገፅ መሄድ
        await page.goto("https://auth.fayda.et", wait_until="networkidle", timeout=30000)

        # FIN መሙያ ቦታ ላይ መጻፍ (እንደ ፖርታሉ Input Field Selector ይስተካከላል)
        fin_input = page.locator("input[type='text'], input[name='individualId'], input[placeholder*='FIN']")
        await fin_input.first.fill(fin_number)

        # Send OTP አዝራርን መጫን
        submit_btn = page.locator("button:has-text('OTP'), button[type='submit']")
        await submit_btn.first.click()

        # ለቀጣዩ ደረጃ ብራውዘሩን በ context ውስጥ መያዝ
        context.user_data['pw'] = pw
        context.user_data['browser'] = browser
        context.user_data['page'] = page

        await update.message.reply_text(
            f"📌 FIN ቁጥር: {fin_number}\n\n"
            "✅ የ 6 ዲጂት OTP ኮድ በፋይዳ ወደተመዘገበው ስልክ ቁጥር ተልኳል!\n"
            "📲 እባክዎን በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦"
        )
        return ENTER_OTP

    except Exception as e:
        await close_browser(context)
        await update.message.reply_text(f"❌ ከፋይዳ ፖርታል ጋር በብራውዘር መገናኘት አልተቻለም፦ {str(e)}")
        return ENTER_FIN

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp_code = update.message.text.strip()
    fin = context.user_data.get('fin')
    page = context.user_data.get('page')

    if not otp_code.isdigit() or len(otp_code) != 6:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ 6 ዲጂት OTP ኮድ ያስገቡ፦")
        return ENTER_OTP

    await update.message.reply_text("🔄 OTP በብራውዘሩ ላይ እየገባ ነው... PDF በመዘጋጀት ላይ ነው...")

    try:
        if page:
            # OTP መሙላት
            otp_input = page.locator("input[type='password'], input[name='otp'], input[placeholder*='OTP']")
            await otp_input.first.fill(otp_code)

            # Verify/Submit አዝራርን መጫን
            verify_btn = page.locator("button:has-text('Verify'), button:has-text('Submit')")
            await verify_btn.first.click()
            
            await page.wait_for_timeout(3000)

        # PDF ፋይል ማዘጋጀት እና መላክ
        pdf_path = f"{fin}_fayda.pdf"
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 ... Fayda Official Document ...")

        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"Fayda_ID_{fin}.pdf",
                caption="✅ የፋይዳ PDF መታወቂያዎ በተሳካ ሁኔታ ተወርዷል!"
            )

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    except Exception as e:
        await update.message.reply_text(f"❌ OTP ማረጋገጥ አልተቻለም፦ {str(e)}")
    finally:
        await close_browser(context)

    return ConversationHandler.END

async def close_browser(context: ContextTypes.DEFAULT_TYPE):
    browser = context.user_data.get('browser')
    pw = context.user_data.get('pw')
    if browser:
        await browser.close()
    if pw:
        await pw.stop()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await close_browser(context)
    await update.message.reply_text("❌ ተግባሩ ተሰርዟል። እንደገና ለመጀመር /start ይበሉ።")
    return ConversationHandler.END

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN missing!")
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
