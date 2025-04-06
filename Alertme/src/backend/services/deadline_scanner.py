from datetime import datetime, timedelta
import schedule
import time
import logging
import sys
from pathlib import Path
from pymongo import MongoClient  # Add this import

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
src_path = project_root / 'src'
sys.path.extend([str(project_root), str(src_path)])

from backend.database.db_connector import db
from backend.services.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    filename='deadline_scanner.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DeadlineScanner:
    def __init__(self):
        self.notification_service = NotificationService()
        self.personal_db = MongoClient('mongodb://your_mongodb_uri')['your_database_name']
        logging.info("Deadline Scanner initialized with personal deadlines database")
    
    def scan_deadlines(self):
        try:
            current_time = datetime.now()
            scheduled_times = [
                (12, 0, "12:00 PM"),
                (14, 0, "2:00 PM"),
                (18, 0, "6:00 PM"),
                (21, 40, "9:40 PM")
            ]
            
            for hour, minute, time_str in scheduled_times:
                if current_time.hour == hour and current_time.minute == minute:
                    logging.info(f"Starting deadline scan at {time_str}")
                    today = current_time.date()
                    
                    # Get deadlines from personal_deadlines_db and government deadlines
                    personal_deadlines = self.personal_db.deadlines.find({})
                    govt_deadlines = db.government_deadlines.find({})
                    
                    # Process personal deadlines
                    for deadline in personal_deadlines:
                        self._process_personal_deadline(deadline, today)
                    
                    # Process government deadlines
                    for deadline in govt_deadlines:
                        self._process_govt_deadline(deadline, today)
                        
                    logging.info(f"Scan completed at {time_str}")
                    break
            
        except Exception as e:
            logging.error(f"Error in deadline scan: {str(e)}")

    def _process_personal_deadline(self, deadline, today):
        try:
            due_date = datetime.strptime(deadline['due_date'], "%Y-%m-%d").date()
            days_until = (due_date - today).days
            
            # Check for various reminder intervals
            if days_until in [30, 15, 7, 3, 1, 0]:
                # Get complete user info directly from main db using user_id
                main_user = db.users.find_one({'_id': deadline['user_id']})
                if main_user:
                    self._send_notifications(main_user, deadline, days_until, is_personal=True)
        except Exception as e:
            logging.error(f"Error processing personal deadline: {str(e)}")

    def _process_govt_deadline(self, deadline, today):
        try:
            due_date = datetime.strptime(deadline['due_date'], "%Y-%m-%d").date()
            days_until = (due_date - today).days
            
            if days_until in [30, 15, 7, 3, 1, 0]:
                logging.info(f"Processing government deadline: {deadline['title']}, due in {days_until} days")
                
                subscribers = deadline.get('subscribers', [])
                if not subscribers:
                    logging.info(f"No subscribers found for government deadline: {deadline['title']}")
                    return
                
                # First find user by email if subscriber is email
                for subscriber in subscribers:
                    if '@' in subscriber:
                        user = db.users.find_one({'email': subscriber})
                    else:
                        user = db.users.find_one({'_id': subscriber})
                        
                    if user:
                        self._send_notifications(user, deadline, days_until, is_personal=False)
                        logging.info(f"Notification sent to subscriber {user.get('email')} for deadline: {deadline['title']}")
                    else:
                        logging.error(f"Could not find user for subscriber: {subscriber}")
                        
        except Exception as e:
            logging.error(f"Error processing government deadline {deadline.get('title', 'Unknown')}: {str(e)}")

    def _send_notifications(self, user, deadline, days_until, is_personal=False):
        try:
            # Set urgency level and emoji based on days remaining
            if days_until == 0:
                urgency = "🔴"  # Due today
                urgency_level = "DUE TODAY"
            elif days_until <= 3:
                urgency = "🟠"  # Very urgent
                urgency_level = "VERY URGENT"
            elif days_until <= 7:
                urgency = "🟡"  # Urgent
                urgency_level = "URGENT"
            elif days_until <= 15:
                urgency = "🟢"  # Moderate
                urgency_level = "MODERATE"
            else:
                urgency = "🔵"  # Normal
                urgency_level = "REMINDER"
            
            deadline_type = "Personal" if is_personal else "Government"
            
            # Create email content
            subject = f"{urgency} {urgency_level}: {deadline['title']}"
            email_message = (
                f"Hello {user['name']},\n\n"
                f"This is a reminder about your {deadline_type.lower()} deadline:\n\n"
                f"Title: {deadline['title']}\n"
                f"Due Date: {deadline['due_date']}\n"
                f"Days Remaining: {days_until}\n"
                f"Priority: {deadline.get('priority', 'N/A')}\n"
                f"Description: {deadline.get('description', 'N/A')}\n"
                f"Status: {deadline.get('status', 'pending')}\n\n"
                f"Urgency Level: {urgency_level}\n\n"
                f"Please ensure to complete this task on time.\n\n"
                f"Best regards,\nAlertMe System"
            )
            
            # Send notifications
            if user.get('email'):
                self.notification_service.send_email_notification(
                    user['email'],
                    subject,
                    email_message
                )
                logging.info(f"Email reminder sent to {user['email']} for {deadline_type} deadline")
                
            if user.get('phone'):
                sms_message = (
                    f"{urgency} {urgency_level}: {deadline['title']} "
                    f"due in {days_until} days. "
                    f"Priority: {deadline.get('priority', 'N/A')}"
                )
                self.notification_service.send_sms_notification(
                    user['phone'],
                    sms_message
                )
                logging.info(f"SMS reminder sent to {user['phone']}")
                
        except Exception as e:
            logging.error(f"Error sending notifications: {str(e)}")

def run_scanner():
    scanner = DeadlineScanner()
    
    # Schedule multiple scan times throughout the day
    schedule.every().day.at("12:00").do(scanner.scan_deadlines)
    schedule.every().day.at("14:00").do(scanner.scan_deadlines)
    schedule.every().day.at("18:00").do(scanner.scan_deadlines)
    schedule.every().day.at("21:40").do(scanner.scan_deadlines)
    
    logging.info("Deadline scanner started - Scheduled for 12:00 PM, 2:00 PM, 6:00 PM, and 9:40 PM daily")
    
    while True:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    run_scanner()