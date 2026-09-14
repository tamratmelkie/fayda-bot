async def handle_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin_number = update.message.text.strip()
    
    if not fin_number.isdigit() or len(fin_number) < 10:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ የ FIN ቁጥር ያስገቡ፦")
        return ENTER_FIN

    context.user_data['fin'] = fin_number
    await update.message.reply_text("🔄 ከፋይዳ ፖርታል ጋር በመገናኘት ላይ... እባክዎን ትንሽ ይጠብቁ...")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    
    try:
        otp_url = f"{FAYDA_BASE_URL}/api/v1/identity/otp/generate"
        payload = {
            "individualId": fin_number,
            "individualIdType": "FIN",
            "otpChannel": ["SMS"]
        }
        
        response = session.post(otp_url, json=payload, timeout=15)
        
        if response.status_code == 200:
            res_data = response.json()
            context.user_data['session'] = session
            await update.message.reply_text(
                f"📌 FIN ቁጥር: {fin_number}\n\n"
                "✅ የ 6 ዲጂት OTP ኮድ በፋይዳ ወደተመዘገበው ስልክ ቁጥር ተልኳል!\n"
                "📲 እባክዎን በስልክዎ የደረሰውን የ 6 ዲጂት OTP ኮድ ያስገቡ፦"
            )
            return ENTER_OTP
        else:
            await update.message.reply_text(
                f"❌ ከፋይዳ ፖርታል የመጣ ኤረር፦ Status Code {response.status_code}\n"
                f"ምላሽ፦ {response.text[:200]}"
            )
            return ENTER_FIN

    except Exception as e:
        await update.message.reply_text(f"❌ ከፋይዳ ፖርታል ጋር መገናኘት አልተቻለም፦ {str(e)}")
        return ENTER_FIN
