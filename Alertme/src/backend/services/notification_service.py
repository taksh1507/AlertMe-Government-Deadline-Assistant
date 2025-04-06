import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os
from dotenv import load_dotenv
import logging

load_dotenv()

class NotificationService:
    def __init__(self):
        # Email configuration
        self.email_sender = os.getenv('SMTP_EMAIL')
        self.email_password = os.getenv('SMTP_PASSWORD')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        # SMS configuration (using Twilio)
        self.twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')

    def send_email_notification(self, recipient, subject, message):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Email sent successfully to {recipient}")
            return True
        except Exception as e:
            logging.error(f"Email notification error: {str(e)}")
            return False

    def send_sms_notification(self, phone_number, message):
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
            data = {
                'To': phone_number,
                'From': self.twilio_phone,
                'Body': message
            }
            response = requests.post(
                url,
                data=data,
                auth=(self.twilio_sid, self.twilio_token)
            )
            
            if response.status_code == 201:
                logging.info(f"SMS sent successfully to {phone_number}")
                return True
            else:
                logging.error(f"SMS failed with status code: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"SMS notification error: {str(e)}")
            return False