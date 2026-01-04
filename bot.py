import os
import time
import requests
import telebot
import schedule
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = telebot.TeleBot(BOT_TOKEN)

MODEL = "mistralai/mistral-7b-instruct"

SYSTEM_PROMPT = """
Kamu adalah Coach Fit, personal gym coach yang suportif, realistis, dan peduli keselamatan.

User berlatih di rumah dengan peralatan terbatas:
- Barbel 10 kg
- 1 dumbbell 5 kg

Semua latihan HARUS menyesuaikan alat tersebut.
Prioritaskan gerakan unilateral, tempo lambat, kontrol penuh, dan repetisi menengah–tinggi (10–20 reps).

User mudah capek, jadi:
- Hindari overtraining
- Frekuensi 3–4x per minggu
- Selalu sediakan opsi recovery atau versi ringan

Fokus utama:
- Form & safety
- Konsistensi jangka panjang
- Progres pelan tapi stabil

Gaya bicara santai, optimistis, jujur, dan membumi.
Boleh toxic (“no pain no gain”).
Jangan menyarankan alat gym lain, suplemen, atau medical advice.
Rayakan progress kecil user.

"""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

WORKOUT_DAYS = [
    "Day 1 – Arm & Shoulder",
    "Day 2 – Chest & Tricep (Ringan)",
    "Day 3 – Back & Bicep (Ringan)",
    "Recovery Day – Istirahat & Stretching"
]

current_day_index = 0

def ask_ai(prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://gym-coach-bot",
        "X-Title": "GymCoachBot"
    }

    r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )

    if not content or not content.strip():
        return "⚠️ AI lagi gak bisa jawab. Coba beberapa detik lagi."

    return content


def post_workout():
    global current_day_index

    try:
        day_title = WORKOUT_DAYS[current_day_index]

        content = ask_ai(
            f"Buatkan postingan channel untuk {day_title}. "
            "Berikan latihan ringan, aman, optimistis, dan realistis."
        )

        message = f"🏋️ {day_title}\n\n{content}"
        bot.send_message(CHANNEL_ID, message)

        current_day_index = (current_day_index + 1) % len(WORKOUT_DAYS)

    except Exception as e:
        print("Error posting workout:", e)

# ================= COMMAND MANUAL =================

@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(
        msg,
        "💪 *Gym Coach Bot aktif*\n\n"
        "Gue coach gym lu.\n"
        "Latihan disesuaikan alat & kondisi.\n\n"
        "Ketik /help buat lihat command.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["help"])
def help_cmd(msg):
    bot.reply_to(
        msg,
        "📋 *Command Gym Coach*\n\n"
        "/hariini – Latihan hari ini\n"
        "/next – Post workout berikutnya ke channel\n"
        "/motivasi – Motivasi singkat\n"
        "/recovery – Recovery & stretching\n"
        "/alat – Info alat latihan\n"
        "/status – Status bot",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["hariini"])
def hari_ini(msg):
    reply = ask_ai(
        "Berikan PROGRAM LATIHAN HARI INI.\n"
        "WAJIB workout, BUKAN recovery.\n"
        "Gunakan barbel 10kg & 1 dumbbell 5kg.\n"
        "Format jelas: exercise, set, rep.\n"
        "Tone santai & optimistis."
    )
    bot.reply_to(msg, reply)

@bot.message_handler(commands=["recovery"])
def recovery(msg):
    reply = ask_ai(
        "Buatkan recovery day ringan.\n"
        "Stretching + mobility.\n"
        "Durasi 10–20 menit.\n"
        "Tanpa alat tambahan."
    )
    bot.reply_to(msg, reply)

@bot.message_handler(commands=["status"])
def status(msg):
    bot.reply_to(
        msg,
        "✅ *Status Bot*\n\n"
        "- Mode: Polling\n"
        "- Scheduler: Aktif\n"
        "- Posting: Senin / Rabu / Jumat\n"
        "- Fokus: Safe & sustainable",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["next"])
def manual_next(msg):
    post_workout()
    bot.reply_to(msg, "✅ Latihan berikutnya dipost ke channel.")

@bot.message_handler(commands=["motivasi"])
def motivasi(msg):
    text = ask_ai("Buatkan motivasi singkat tentang konsistensi latihan.")
    bot.reply_to(msg, text)

@bot.message_handler(func=lambda m: True)
def chat(msg):
    try:
        reply = ask_ai(msg.text)
        bot.reply_to(msg, reply)
    except Exception as e:
        bot.reply_to(msg, "⚠️ Lagi capek bentar, coba lagi ya.")

# ================= SCHEDULER =================

# Posting 3x seminggu (AMAN)
schedule.every().monday.at("08:00").do(post_workout)
schedule.every().wednesday.at("08:00").do(post_workout)
schedule.every().friday.at("08:00").do(post_workout)

print("Gym Coach Bot running with scheduler & polling...")

while True:
    try:
        bot.polling(non_stop=True, timeout=60)
    except Exception as e:
        print("Polling error:", e)
        time.sleep(5)

    schedule.run_pending()
    time.sleep(1)

print("Gym Coach Bot running with scheduler & polling...")
bot.infinity_polling(skip_pending=True)
