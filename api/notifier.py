import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# For Vercel, the user will need to define these in the Environment Variables dashboard.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
try:
    # Safely parse port, fallback to 587 if user entered empty string or letters
    port_str = os.getenv("SMTP_PORT", "587").strip()
    SMTP_PORT = int(port_str if port_str else 587)
except ValueError:
    SMTP_PORT = 587
    
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()

def send_notification_email(to_email, irl_number, status, decision_date):
    if not SMTP_USER or not SMTP_PASS:
        print(f"⚠️ SMTP credentials not configured. Skipping email to {to_email}")
        return False
        
    subject = f"Irish Visa Update: Decision published for {irl_number}"
    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <h2 style="color: #15803d;">Irish Visa Tracker Update</h2>
            <p>Hello,</p>
            <p>You requested to be notified when a decision was made for your application. We have good news—a decision has just been published by the Embassy in New Delhi!</p>
            
            <div style="background-color: #f3f4f6; padding: 15px; border-left: 4px solid #15803d; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Reference Number:</strong> {irl_number}</p>
                <p style="margin: 5px 0;"><strong>Decision Status:</strong> {status}</p>
                <p style="margin: 5px 0;"><strong>Decision Date:</strong> {decision_date}</p>
            </div>
            
            <p>You can verify this information on the <a href="https://www.ireland.ie/en/india/newdelhi/services/visas/processing-times-and-decisions/#visa-decisions" style="color: #15803d;">Official Embassy Website</a>.</p>
            <br>
            <p>Best regards,<br><strong>Visa Tracker Automation System</strong></p>
        </body>
    </html>
    """
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Visa Tracker Automation <{SMTP_USER}>"
    msg["To"] = to_email
    
    msg.attach(MIMEText(html, "html"))
    
    try:
        # Added timeout=5 so Vercel doesn't crash the function if Google blocks the connection
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False
