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

DAY_FILE = "day.txt"

def get_day():
    if not os.path.exists(DAY_FILE):
        with open(DAY_FILE, "w") as f:
            f.write("1")
        return 1
    with open(DAY_FILE) as f:
        return int(f.read().strip())

def set_day(day: int):
    with open(DAY_FILE, "w") as f:
        f.write(str(day))


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

    def clean_output(text: str) -> str:
        if not text:
            return text

        BAD_TOKENS = ["<s>", "</s>"]
        for t in BAD_TOKENS:
            text = text.replace(t, "")

        return text.strip()
    
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

    content = clean_output(content)
    return content



def post_workout():
    day = get_day()

    try:
        content = ask_ai(
            f"IKUTI FORMAT DI BAWAH INI SECARA KETAT.\n"
            f"JANGAN TAMBAH APA PUN DI LUAR FORMAT.\n"
            f"MAKSIMAL 3 LATIHAN, MAKSIMAL 3 SET.\n\n"
            f"FORMAT OUTPUT (WAJIB SAMA):\n"
            f"Day {day}\n"
            f"- Barbel curl 8x - 3 repeat\n\n"
            f"- Dumbbell Shoulder press 12x - 2 repeat\n\n"
            f"- Two-Hand Overhead Dumbbell Tricep Extension 15x - 2 repeat\n\n"
            f"RULE:\n"
            f"- Gunakan HANYA barbel 10kg & dumbbell 5kg\n"
            f"- Jangan beri penjelasan\n"
            f"- Jangan beri motivasi\n"
            f"- Jangan pakai emoji\n"
            f"- Output TEKS SAJA\n\n"
            f"Sekarang buatkan PROGRAM LATIHAN HARI INI."
        )

        message = content
        bot.send_message(CHANNEL_ID, message)

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
        "/resetday - Reset hari count ke 1"
        "/harike {angka} - Set hari ke berapa"
        "/status – Status bot",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["harike"])
def set_hari_ke(msg):
    parts = msg.text.split()
    if len(parts) != 2:
        bot.reply_to(msg, "❌ Format: /harike 2")
        return

    try:
        day = int(parts[1])
        if day < 1:
            raise ValueError
        set_day(day)
        bot.reply_to(msg, f"✅ Hari latihan diset ke Day {day}")
    except ValueError:
        bot.reply_to(msg, "❌ Angka tidak valid. Contoh: /harike 1")


@bot.message_handler(commands=["hariini"])
def hari_ini(msg):
    day = get_day()

    reply = ask_ai(
        f"IKUTI FORMAT DI BAWAH INI SECARA KETAT.\n"
        f"JANGAN TAMBAH APA PUN DI LUAR FORMAT.\n"
        f"MAKSIMAL 3 LATIHAN, MAKSIMAL 3 SET.\n\n"
        f"FORMAT OUTPUT (WAJIB SAMA):\n"
        f"Day {day}\n"
        f"- Barbel curl 8x - 3 repeat\n\n"
        f"- Dumbbell Shoulder press 12x - 2 repeat\n\n"
        f"- Two-Hand Overhead Dumbbell Tricep Extension 15x - 2 repeat\n\n"
        f"RULE:\n"
        f"- Gunakan HANYA barbel 10kg & dumbbell 5kg\n"
        f"- Jangan beri penjelasan\n"
        f"- Jangan beri motivasi\n"
        f"- Jangan pakai emoji\n"
        f"- Output TEKS SAJA\n\n"
        f"Sekarang buatkan PROGRAM LATIHAN HARI INI."
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

@bot.message_handler(commands=["resetday"])
def reset_day(msg):
    with open(DAY_FILE, "w") as f:
        f.write("1")
    bot.reply_to(msg, "🔄 Day direset ke Day 1.")


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
