import json
import os
import pyotp
import telebot
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired

# আপনার বট টোকেন দিন (এনভায়রনমেন্ট ভ্যারিয়েবল অথবা সরাসরি কোটেশনের ভেতর)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")

if BOT_TOKEN == "8853741710:AAGpdHTtYo2QfyiPmCDXxfJ7bVkK1bFhpcQ":
    print(
        "[!] সতর্কতা: BOT_TOKEN পরিবর্তন করুন অথবা এনভায়রনমেন্টে সেট করুন।"
    )

bot = telebot.TeleBot(BOT_TOKEN)


def generate_otp(secret_key: str) -> str:
    """2FA Secret Key থেকে লাইভ ৬ ডিজিটের OTP তৈরি করে"""
    clean_key = secret_key.replace(" ", "").strip()
    return pyotp.TOTP(clean_key).now()


@bot.message_handler(commands=["start"])
def send_welcome(message):
    reply_text = (
        "👋 **Instagram 2FA Cookie Extractor**\n\n"
        "দয়া করে এভাবে তথ্য পাঠান:\n"
        "`username password 2fa_key`"
    )
    bot.send_message(message.chat.id, reply_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def process_login(message):
    parts = message.text.strip().split()

    if len(parts) != 3:
        bot.send_message(
            message.chat.id,
            "❌ ভুল ফরম্যাট! অনুগ্রহ করে এভাবে পাঠান:\n`username password 2fa_key`",
            parse_mode="Markdown",
        )
        return

    username, password, two_fa_key = parts[0], parts[1], parts[2]
    wait_msg = bot.send_message(
        message.chat.id, "⏳ 2FA কোড দিয়ে লগইন প্রসেস করা হচ্ছে..."
    )

    try:
        # ১. OTP কোড জেনারেট
        otp_code = generate_otp(two_fa_key)

        cl = Client()

        # ২. লগইন ও 2FA হ্যান্ডলিং
        try:
            cl.login(username, password, verification_code=otp_code)
        except TwoFactorRequired:
            cl.two_factor_login(otp_code)

        # ৩. সেশন কুকিজ নেওয়া
        cookies = cl.cookie_dict

        if not cookies or "sessionid" not in cookies:
            bot.edit_message_text(
                "❌ লগইন করা সম্ভব হয়নি। ইউজারনেম/পাসওয়ার্ড/2FA কী পুনরায় চেক করুন।",
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
            )
            return

        # সহজে কপি করার উপযোগী ফরম্যাট
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        json_cookies = json.dumps(cookies, indent=2)

        bot.delete_message(message.chat.id, wait_msg.message_id)

        # রেজাল্ট পাঠানো (ট্যাপ করলেই পুরোটা কপি হবে)
        result_text = (
            f"📋 **Cookie String (ট্যাপ করলেই কপি):**\n"
            f"```text\n{cookie_string}\n```\n\n"
            f"📦 **Cookie JSON:**\n"
            f"```json\n{json_cookies}\n```"
        )
        bot.send_message(message.chat.id, result_text, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(
            f"❌ এরর এসেছে!\n`{str(e)}`",
            chat_id=message.chat.id,
            message_id=wait_msg.message_id,
            parse_mode="Markdown",
        )


if __name__ == "__main__":
    print("[+] বট চালু রয়েছে...")
    bot.infinity_polling()
