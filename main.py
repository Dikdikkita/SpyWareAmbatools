import os
import platform
import cv2
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Konfigurasi
TOKEN = "8170122656:AAEvPa3XPHZr6BAf6kA69wOxYoFojlroflo"
ALLOWED_USER_ID = 6448306853
current_directory = os.getcwd()

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
    "message": "Membuat file teks di Desktop (contoh: /message Ini pesan saya)"
}

async def check_auth(update: Update) -> bool:
    """Memeriksa apakah pengguna diizinkan mengakses bot"""
    if update.effective_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("Akses ditolak. Anda tidak memiliki izin.")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle perintah /start"""
    if not await check_auth(update):
        return
    
    computer_name = platform.node()
    await update.message.reply_text(f"Komputer {computer_name} aktif!")

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
        image_path = f"capture_{timestamp}.jpg"
        
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
            await update.message.reply_text("Silakan masukkan pesan yang ingin disimpan.\nContoh: /message Ini adalah pesan saya")
            return
        
        # Gabungkan semua argumen menjadi satu pesan
        message_text = " ".join(context.args)
        
        # Buat nama file dengan timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"message_{timestamp}.txt"
        
        # Buat path lengkap ke Desktop
        file_path = os.path.join(DESKTOP_PATH, file_name)
        
        # Tambahkan informasi timestamp ke dalam pesan
        full_message = f"Pesan dibuat pada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{message_text}"
        
        # Pastikan folder Desktop ada
        if not os.path.exists(DESKTOP_PATH):
            await update.message.reply_text(f"Error: Folder Desktop tidak ditemukan di {DESKTOP_PATH}")
            return
        
        # Tulis pesan ke file di Desktop
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(full_message)
        
        await update.message.reply_text(
            f"Pesan berhasil disimpan di Desktop!\n"
            f"Nama file: {file_name}\n"
            f"Lokasi: {DESKTOP_PATH}\n"
            f"Isi pesan: {message_text}"
        )
        
    except Exception as e:
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

def main():
    """Fungsi utama untuk menjalankan bot"""
    # Membuat aplikasi
    application = Application.builder().token(TOKEN).build()
    
    # Menambahkan handler
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cd", cd_command))
    application.add_handler(CommandHandler("ls", ls_command))
    application.add_handler(CommandHandler("dwd", download_command))
    application.add_handler(CommandHandler("capture", capture_command))
    application.add_handler(CommandHandler("message", message_command))
    
    # Menambahkan error handler
    application.add_error_handler(error_handler)
    
    # Jalankan pengecekan folder Desktop
    if not os.path.exists(DESKTOP_PATH):
        print(f"Peringatan: Folder Desktop tidak ditemukan di {DESKTOP_PATH}")
    
    # Menjalankan bot
    print("Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()