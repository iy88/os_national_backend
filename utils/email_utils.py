import random
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from email.mime.text import MIMEText

from flask import current_app

from utils.redis_client import set_verification_code


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def generate_verification_code() -> str:
    return str(random.randint(100000, 999999))


def send_verification_email(email: str, code: str):
    set_verification_code(email, code)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = '【城竞共生】 您的注册验证码'
    sender = current_app.config['SMTP_SENDER']
    sender_name = current_app.config.get('SMTP_SENDER_NAME', '城竞共生')
    msg['From'] = formataddr((Header(sender_name, 'utf-8').encode(), sender))
    msg['To'] = email

    html_content = f'''
    <html>
    <body>
        <h2>您好，</h2>
        <p>您的注册验证码是: <strong>{code}</strong></p>
        <p>验证码有效期为 5 分钟，请尽快完成注册。</p>
        <p>如果您没有发起注册请求，请忽略此邮件。</p>
    </body>
    </html>
    '''
    msg.attach(MIMEText(html_content, 'html'))

    try:
        if current_app.config.get('SMTP_USE_SSL'):
            with smtplib.SMTP_SSL(current_app.config['SMTP_SERVER'],
                                  current_app.config['SMTP_PORT']) as server:
                server.login(current_app.config['SMTP_USERNAME'],
                             current_app.config['SMTP_PASSWORD'])
                server.sendmail(current_app.config['SMTP_SENDER'],
                                [email], msg.as_string())
        else:
            with smtplib.SMTP(current_app.config['SMTP_SERVER'],
                              current_app.config['SMTP_PORT']) as server:
                server.starttls()
                server.login(current_app.config['SMTP_USERNAME'],
                             current_app.config['SMTP_PASSWORD'])
                server.sendmail(current_app.config['SMTP_SENDER'],
                                [email], msg.as_string())
    except smtplib.SMTPResponseException as e:
        # SMTP专用异常，携带服务器响应码和响应文本
        raise RuntimeError(f'Email send failed: {e.smtp_code} {e.smtp_error.decode("utf-8") if e.smtp_error else str(e)}')
    except smtplib.SMTPException as e:
        raise RuntimeError(f'Email send failed: SMTP error {e}')
    except Exception as e:
        raise RuntimeError(f'Email send failed: {e}')
