import os
import secrets
import string
import email
from email import policy
from email.utils import parseaddr
from flask import Blueprint, jsonify, request, render_template
from app.models import save_email, get_inbox, register_inbox, is_inbox_active, INBOX_TTL_SECONDS
from app.extensions import limiter

# -------------------------------------------------------------------
# Configuration & Blueprint Setup
# -------------------------------------------------------------------
main_bp = Blueprint("main", __name__)

# The domain used for your temporary addresses
DOMAIN = "techwithap.site"


def generate_random_string(length=36):
    """
    Generates a cryptographically secure random alphanumeric string
    using Python's secrets module (e.g., 'a9x8k2m1q...').
    """
    allowed_chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(allowed_chars) for _ in range(length))


# -------------------------------------------------------------------
# Route 1: Render the Frontend Interface
# -------------------------------------------------------------------
@main_bp.route("/", methods=["GET"])
def index():
    """Serves the main web dashboard (HTML/CSS/JS)."""
    return render_template("index.html")


# -------------------------------------------------------------------
# Route 2: Generate a Disposable Email
# -------------------------------------------------------------------
@main_bp.route("/generate", methods=["GET"])
@limiter.limit("5 per minute") # Prevent users from spam-generating emails
def generate_email():
    """
    Creates a new random temporary email address and returns it to the client.
    TTL is 180 seconds (3 minutes), matching the Redis expiration in models.py.
    """
    username = generate_random_string()
    email_address = f"{username}@{DOMAIN}"

    # Register this inbox in Redis — marks it as alive and eligible to receive emails
    register_inbox(email_address)

    return jsonify({
        "status": "success",
        "email": email_address,
        "ttl_seconds": INBOX_TTL_SECONDS,
    }), 200


# -------------------------------------------------------------------
# Route 3: Fetch Inbox Messages
# -------------------------------------------------------------------
@main_bp.route("/inbox/<email_address>", methods=["GET"])
@limiter.limit("30 per minute")
def fetch_inbox(email_address):
    """
    Queries Redis for any messages stored under the specified email key.
    Returns the list of received emails and the remaining lifetime (TTL).
    """
    # Basic validation check
    if not email_address or "@" not in email_address:
        return jsonify({
            "status": "error",
            "message": "Invalid email address format."
        }), 400

    # Fetch stored emails and remaining expiration seconds from Redis
    inbox_data = get_inbox(email_address.strip().lower())

    # If the inbox has expired or was never generated, tell the client explicitly
    if inbox_data.get("expired"):
        return jsonify({
            "status": "expired",
            "email": email_address,
            "expires_in_seconds": 0,
            "count": 0,
            "emails": [],
            "message": "This inbox has expired and been destroyed. Generate a new email."
        }), 200

    return jsonify({
        "status": "success",
        "email": email_address,
        "expires_in_seconds": inbox_data["expires_in_seconds"],
        "count": len(inbox_data["emails"]),
        "emails": inbox_data["emails"],
    }), 200


# -------------------------------------------------------------------
# Route 4: Inbound Email Webhook Receiver
# -------------------------------------------------------------------

def get_recipient_email() :
    # Attempt to pull the recipient from a custom header first (Best Practice)
    # Fallback to a global bucket if the header is missing
    return request.headers.get("X-Forwarded-To", "global_inbox")

@main_bp.route("/webhook/email", methods=["POST"])
@limiter.limit("5 per minute", key_func=get_recipient_email) # Max 5 emails per minute per inbox
def receive_webhook():
    """
    Receives raw email data forwarded by the Cloudflare Worker,
    parses headers and message body, and persists the payload into Redis.
    """
    # 1. Security Check: Verify secret header against environment variable
    secret = request.headers.get("X-Webhook-Secret", "")
    expected_secret = os.environ.get("WEBHOOK_SECRET", "super-secret-key")

    if not secrets.compare_digest(secret, expected_secret):
        return jsonify({"error": "Unauthorized"}), 401

    # 2. Check if the target inbox is still alive BEFORE parsing the email
    #    This rejects emails to expired/never-generated addresses early.
    recipient_header = request.headers.get("X-Forwarded-To", "").strip().lower()
    if recipient_header and not is_inbox_active(recipient_header):
        return jsonify({
            "error": "Inbox expired or does not exist",
            "recipient": recipient_header
        }), 410  # 410 Gone — the resource existed but has been destroyed

    # 3. Extract the raw email string from the incoming HTTP request body
    raw_email_data = request.get_data(as_text=True)
    if not raw_email_data:
        return jsonify({"error": "Empty payload"}), 400

    # 3. Parse the standard RFC 822 email format into a Python object
    msg = email.message_from_string(raw_email_data, policy=policy.default)

    # 4. Extract basic metadata (with sensible fallbacks)
    subject = msg.get("subject", "(No Subject)")
    sender = msg.get("from", "Unknown Sender")
    date_str = msg.get("date", "")

    # Clean the recipient address (handles formats like 'User Name <user@temp.techwithap.site>')
    _, recipient_clean = parseaddr(msg.get("to", ""))
    recipient_clean = recipient_clean.lower()

    # 5. Extract message content (Plain Text and/or HTML)
    body_text = ""
    body_html = ""

    if msg.is_multipart():
        # Iterate over all email parts (attachments, body layers, etc.)
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Skip file attachments to process only textual content
            if "attachment" not in content_disposition:
                charset = part.get_content_charset("utf-8") or "utf-8"
                try:
                    payload_decoded = part.get_payload(decode=True).decode(charset, errors="replace")
                    if content_type == "text/plain":
                        body_text = payload_decoded
                    elif content_type == "text/html":
                        body_html = payload_decoded
                except Exception:
                    pass
    else:
        # Single-part simple email
        charset = msg.get_content_charset("utf-8") or "utf-8"
        try:
            body_text = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            pass

    # 6. Build the final structured payload
    payload = {
        "sender": sender,
        "recipient": recipient_clean,
        "subject": subject,
        "body": body_text,
        "html": body_html,
        "date": date_str
    }

    # 7. Save to Redis under the recipient key
    # 8. Final gate: verify inbox is still active before saving
    #    (defense-in-depth — catches edge case where inbox expires between
    #     the header check and this point)
    if recipient_clean:
        if not is_inbox_active(recipient_clean):
            return jsonify({
                "error": "Inbox expired or does not exist",
                "recipient": recipient_clean
            }), 410

        save_email(recipient_clean, payload)
        return jsonify({"status": "saved", "recipient": recipient_clean}), 200

    return jsonify({"error": "No valid recipient found in email"}), 400


# -------------------------------------------------------------------
# Route 5: Inbox Active Check (used by Cloudflare Worker pre-flight)
# -------------------------------------------------------------------
@main_bp.route("/inbox/check/<email_address>", methods=["GET"])
def check_inbox_active(email_address):
    """
    Lightweight endpoint for the Cloudflare Worker to check if an inbox
    is still alive before forwarding the email. Returns 200 if active,
    404 if expired or never generated.
    """
    if is_inbox_active(email_address.strip().lower()):
        return jsonify({"status": "active"}), 200
    else:
        return jsonify({"status": "expired"}), 404