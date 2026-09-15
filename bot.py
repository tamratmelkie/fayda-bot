async def handle_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin_number = update.message.text.strip()
    
    if not fin_number.isdigit() or len(fin_number) < 10:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ FIN ቁጥር ያስገቡ፦")
        return ENTER_FIN

    context.user_data['fin'] = fin_number
    await update.message.reply_text("🔄 ብራውዘር እየተከፈተ ነው... ከፋይዳ ፖርታል ጋር በመገናኘት ላይ...")

    try:
        pw = await async_playwright().start()
        try:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
        except Exception:
            # ብራውዘሩ ካልተገኘ በራሱ በራስ-ሰር ይጭነዋል
            import subprocess
            subprocess.run(["python", "-m", "playwright", "install", "chromium"])
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

        browser_context = await browser.new_context()
        page = await browser_context.new_page()

        await page.goto("https://auth.fayda.et", wait_until="networkidle", timeout=30000)

        fin_input = page.locator("input[type='text'], input[name='individualId'], input[placeholder*='FIN']")
        await fin_input.first.fill(fin_number)

        submit_btn = page.locator("button:has-text('OTP'), button[type='submit']")
        await submit_btn.first.click()

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
