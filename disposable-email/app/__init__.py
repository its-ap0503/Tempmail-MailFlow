# initialises flask application and configuration 
from flask import Flask
import os
from app.extensions import limiter
from flask import jsonify


def create_app():
    # 1. Instantiate the flask object 
    """
    Application Factory Pattern: Instantiates and configures
    the Flask application instance.
    """
    app = Flask(__name__)

    # 2. Configure app settings from environment or defaults
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-12345")

    # Initialize the limiter with the app
    limiter.init_app(app)

    # Importing here inside the function prevents circular dependency issues
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Catch 429 errors and return JSON instead of HTML
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "status": "error",
            "message": f"Rate limit exceeded: {e.description}"
        }), 429
    
    return app
