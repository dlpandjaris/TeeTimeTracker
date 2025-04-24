import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Email credentials
sender_email = 'dlpandjaris@gmail.com'  # Replace with your email
receiver_email = 'dlpandjaris@gmail.com'  # Replace with your email (same as sender to send to yourself)
password = 'huwb uwop fehw ydig'  # Use your Gmail password or App Password if 2FA is enabled

# Email content
def make_email(body: str):
  subject = 'Tee Times Found'

  # Create a MIME object for the email
  msg = MIMEMultipart()
  msg['From'] = sender_email
  msg['To'] = receiver_email
  msg['Subject'] = subject
  msg.attach(MIMEText(body, 'plain'))

  return msg


def send_email(msg):
  # Establish an SMTP session
  try:
    server = smtplib.SMTP('smtp.gmail.com', 587)  # Use Gmail's SMTP server
    server.starttls()  # Secure the connection
    server.login(sender_email, password)  # Log into your email account

    # Send the email
    text = msg.as_string()
    server.sendmail(sender_email, receiver_email, text)

    print("Email sent successfully!")

  except Exception as e:
    print(f"Error: {e}")

  finally:
    server.quit()  # Close the server connection