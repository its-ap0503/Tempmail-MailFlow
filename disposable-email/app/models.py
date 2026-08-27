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


def save_email(email_address, payload):
    """
    Saves a complete email payload dictionary into a Redis list.
    Resets the 3-minute self-destruct timer every time a new email arrives.
    """
    key = f"inbox:{email_address}"

    # Push the JSON payload to the front of the list
    db.lpush(key, json.dumps(payload))

    # Set/Reset the 3-minute self-destruct timer
    db.expire(key, INBOX_TTL_SECONDS)


def get_inbox(email_address):
    """
    Retrieves all stored emails for the given address and calculates remaining time.
    """
    key = f"inbox:{email_address}"

    # Check remaining time-to-live (TTL)
    ttl = db.ttl(key)

    # If key doesn't exist or expired, ttl is -2. Return empty state.
    if ttl < 0:
        return {"expires_in_seconds": 0, "emails": []}

    # Fetch all raw JSON strings from the list
    raw_emails = db.lrange(key, 0, -1)

    # Parse them back into Python dictionaries
    parsed_emails = [json.loads(email) for email in raw_emails]

    return {
        "expires_in_seconds": ttl,
        "emails": parsed_emails
    }