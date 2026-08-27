import redis
import json
import os

# Connect to Redis
db = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True,
    protocol=2
)

def save_email(email_address, payload):
    """
    Saves a complete email payload dictionary into a Redis list.
    Sets a 10-minute (600 second) expiration timer.
    """
    key = f"inbox:{email_address}"
    
    # Push the JSON payload to the front of the list
    db.lpush(key, json.dumps(payload))
    
    # Set/Reset the 10-minute self-destruct timer
    db.expire(key, 600)

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