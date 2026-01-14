import telebot
import sqlite3
import threading
from flask import Flask, request
import os
# --- 1. إعدادات البوت ---
# استبدل النص التالي بالتوكين الذي حصلت عليه من BotFather
API_TOKEN = os.getenv('BOT_TOKEN')

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- 2. إعداد قاعدة البيانات (SQLite) ---
def init_db():
    conn = sqlite3.connect('files.db', check_same_thread=False)
    c = conn.cursor()
    # إنشاء جدول لحفظ: اسم الملف، معرف الملف، ونوعه
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (name TEXT, file_id TEXT, file_type TEXT)''')
    conn.commit()
    return conn, c

conn, cursor = init_db()

# --- 3. سيرفر الويب الوهمي (للبقاء متصلاً) ---
@app.route('/')
def home():
    return "I am alive! Bot is running."

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# --- 4. منطق البوت الذكي ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_msg = (
        "مرحباً بك! 🤖\n"
        "أنا بوت أرشيف ذكي. \n\n"
        "📥 **للحفظ:** فقط أرسل لي أي ملف (صورة، فيديو، pdf) وسأقوم بفرزه وحفظه.\n"
        "📤 **للاسترجاع:** اكتب اسم الملف الذي تبحث عنه."
    )
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

# دالة لحفظ البيانات في قاعدة البيانات
def save_to_db(name, file_id, f_type):
    try:
        cursor.execute("INSERT INTO files VALUES (?, ?, ?)", (name, file_id, f_type))
        conn.commit()
        return True
    except:
        return False

# استقبال الملفات وفرزها
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_files(message):
    file_id = None
    file_name = None
    file_type = "غير معروف"

    # فرز ذكي حسب نوع الرسالة
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_type = "مستند 📁"
    elif message.photo:
        file_id = message.photo[-1].file_id # نأخذ أعلى جودة
        file_name = f"image_{message.id}.jpg" # نعطي اسماً افتراضياً للصور
        file_type = "صورة 🖼"
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or f"video_{message.id}.mp4"
        file_type = "فيديو 🎥"
    
    if file_id:
        save_to_db(file_name, file_id, file_type)
        bot.reply_to(message, f"✅ تم الحفظ بنجاح!\nالاسم: {file_name}\nالتصنيف: {file_type}")

# البحث واسترجاع الملفات
@bot.message_handler(func=lambda message: True) # يستقبل أي نص
def search_file(message):
    search_query = message.text
    
    # نبحث عن أي ملف يحتوي اسمه على النص المرسل
    cursor.execute("SELECT name, file_id, file_type FROM files WHERE name LIKE ?", ('%'+search_query+'%',))
    results = cursor.fetchall()

    if not results:
        bot.reply_to(message, "❌ لم أجد ملفاً بهذا الاسم.")
        return

    # إذا وجدنا ملفات، نرسلها
    if len(results) > 3:
        bot.reply_to(message, "وجد عدد كبير من النتائج، سأرسل أول 3 فقط.")
    
    for row in results[:3]: # نرسل أول 3 نتائج فقط لتجنب الإزعاج
        f_name, f_id, f_type = row
        try:
            bot.send_document(message.chat.id, f_id, caption=f"الاسم: {f_name}\nالنوع: {f_type}")
        except:
            bot.reply_to(message, f"وجدت الملف {f_name} لكن حدث خطأ في إرساله.")

# --- 5. التشغيل ---
if __name__ == '__main__':
    # تشغيل سيرفر الويب في خيط منفصل
    t = threading.Thread(target=run_web_server)
    t.start()
    
    # تشغيل البوت
    print("Bot is running...")

    bot.infinity_polling()
