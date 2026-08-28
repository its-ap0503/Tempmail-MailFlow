# we will be adding the rate limiter here 
import os
from flask import request
from flask_limiter import Limiter

# If you are behind Cloudflare, you must use CF-Connecting-IP to get the real user IP, 
# otherwise all requests will look like they come from Cloudflare's servers.
def get_real_ip():
    return request.headers.get("CF-Connecting-IP", request.remote_addr)


limiter = Limiter(
    key_func=get_real_ip,
    storage_uri=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    strategy="fixed-window"  # Fixed Window Standard rate limiting algorithm
)