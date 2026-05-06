import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

def send_register_mail(username, user_email):
    TO_EMAIL = "taichinhpro123@gmail.com"

    content = f"""
    Có người vừa đăng ký tài khoản mới

    Username: {username}
    Email: {user_email}
    """

    msg = MIMEText(content)

    msg["Subject"] = "Có user mới đăng ký"
    msg["From"] = formataddr(("GetGoals TOEIC", EMAIL))
    msg["To"] = TO_EMAIL

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(EMAIL, PASSWORD)

        server.send_message(msg)

        print("Đã gửi mail thông báo")

    except Exception as e:
        print("Lỗi gửi mail:", e)

    finally:
        server.quit()