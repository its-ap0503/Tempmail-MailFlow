import redis
import json
import os

# Connect to Redis using a full connection URL.
# Render's managed Redis gives you a single REDIS_URL like:
#   redis://red-xxxxxxxxxxxx:6379
# Locally (no env var set) this falls back to a plain localhost Redis.
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
db = redis.from_url(redis_url, decode_responses=True)

# Self-destruct timer: 3 minutes
INBOX_TTL_SECONDS = 180


# -------------------------------------------------------------------
# Inbox Lifecycle: Register → Active → Expired (auto-destroyed)
# -------------------------------------------------------------------

def register_inbox(email_address):
    """
    Creates an 'active:{email}' key in Redis with the standard TTL.
    This marks the inbox as alive and eligible to receive emails.
    Called once when /generate creates a new address.
    """
    active_key = f"active:{email_address}"
    db.set(active_key, "1", ex=INBOX_TTL_SECONDS)


def is_inbox_active(email_address):
    """
    Returns True if the inbox was generated and hasn't expired yet.
    Checks for the existence of the 'active:{email}' key in Redis.
    """
    return db.exists(f"active:{email_address}") == 1


def delete_inbox(email_address):
    """
    Immediately destroys an inbox — removes both the active flag
    and all stored emails. Used for manual cleanup if needed.
    """
    db.delete(f"active:{email_address}", f"inbox:{email_address}")


# -------------------------------------------------------------------
# Email Storage
# -------------------------------------------------------------------

def save_email(email_address, payload):
    """
    Saves a complete email payload dictionary into a Redis list.
    Resets the 3-minute self-destruct timer on BOTH the inbox
    and the active flag every time a new email arrives.
    """
    inbox_key = f"inbox:{email_address}"
    active_key = f"active:{email_address}"

    # Push the JSON payload to the front of the list
    db.lpush(inbox_key, json.dumps(payload))

    # Set/Reset the 3-minute self-destruct timer on both keys
    db.expire(inbox_key, INBOX_TTL_SECONDS)
    db.expire(active_key, INBOX_TTL_SECONDS)


def get_inbox(email_address):
    """
    Retrieves all stored emails for the given address and calculates remaining time.
    """
    active_key = f"active:{email_address}"
    inbox_key = f"inbox:{email_address}"

    # Check if the inbox is still active
    if not db.exists(active_key):
        return {"expires_in_seconds": 0, "emails": [], "expired": True}

    # Check remaining time-to-live (TTL)
    ttl = db.ttl(active_key)

    # If key doesn't exist or expired, ttl is -2. Return expired state.
    if ttl < 0:
        return {"expires_in_seconds": 0, "emails": [], "expired": True}

    # Fetch all raw JSON strings from the list
    raw_emails = db.lrange(inbox_key, 0, -1)

    # Parse them back into Python dictionaries
    parsed_emails = [json.loads(email) for email in raw_emails]

    return {
        "expires_in_seconds": ttl,
        "emails": parsed_emails,
        "expired": False
    }