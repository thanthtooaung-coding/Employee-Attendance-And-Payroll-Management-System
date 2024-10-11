import random, string
import smtplib

from flask import redirect, render_template, session, current_app
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def apology(message, code=400, title=""):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message), title=title), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def role_required(roles):
    """
    Decorator to restrict access to users with specific roles.
    
    :param roles: List of roles allowed to access the route
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('user_role')
            if user_role not in roles:
                # Redirect to some page, like a "no access" page or their profile
                return redirect("/profile")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def generate_readable_password(length=8):
    """Generate a random user-readable password."""

    characters = string.ascii_letters + string.digits  # e.g., 'abcABC123'
    
    # Generate a password by randomly choosing characters
    password = ''.join(random.choice(characters) for _ in range(length))
    
    return password


def send_email(recipient_email, password):
    """Send an email with the generated password to the user."""
    
    # Sender email configuration
    sender_email = current_app.config['MAIL_USERNAME']
    sender_password = current_app.config['MAIL_PASSWORD']
    subject = "Your Account Password"
    body = f"Hello,\n\nYour generated password is: {password}\n\nBest regards,\nVinnTrack"

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def usd(value):
    """Format value as USD."""
    
    return f"${value:,}"