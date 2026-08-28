from dotenv import load_dotenv
load_dotenv()  # This must be at the very top!


import os
from app import create_app
# ... the rest of your run.py code

# 1. Instantiate the application using the factory function
app = create_app()

if __name__ == "__main__":
    # 2. Extract port from environment (for cloud deployment) or default to 5000
    port = int(os.environ.get("PORT", 5000))

    # 3. Launch the development server
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )