import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import os
from dotenv import load_dotenv

# Load lại env để chắc chắn có dữ liệu
load_dotenv()

def send_welcome_email(user_email: str, user_name: str):
    """
    Gửi email chào mừng cho người dùng mới đăng ký.
    """
    # Lấy thông tin từ env, xóa khoảng trắng nếu có
    EMAIL = os.getenv("EMAIL", "").strip().replace('"', '')
    PASSWORD = os.getenv("PASSWORD", "").strip().replace('"', '').replace(' ', '')
    
    if not EMAIL or not PASSWORD:
        print(f"DEBUG: Mail Config Error - EMAIL: '{EMAIL}', PASSWORD: {'set' if PASSWORD else 'not set'}")
        print("Lỗi: Chưa cấu hình EMAIL hoặc PASSWORD trong file .env")
        return
    
    print(f"DEBUG: Using EMAIL: {EMAIL}")

    content = f"""
    Chào mừng {user_name} đến với GetGoals TOEIC!
    
    Tài khoản của bạn đã được đăng ký thành công với email: {user_email}.
    Chúc bạn có những trải nghiệm học tập tuyệt vời và sớm đạt được mục tiêu TOEIC của mình!
    
    Trân trọng,
    Đội ngũ GetGoals TOEIC.
    """

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = "Chào mừng bạn đến với GetGoals TOEIC"
    msg["From"] = formataddr(("GetGoals TOEIC", EMAIL))
    msg["To"] = user_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)
        print(f"Đã gửi mail chào mừng tới {user_email}")
    except Exception as e:
        print(f"Lỗi khi gửi mail chào mừng: {e}")
    finally:
        try:
            server.quit()
        except:
            pass

