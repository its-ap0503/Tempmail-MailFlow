# initialises flask application and configuration 
from flask import Flask
import os

def create_app():
    # 1. Instantiate the flask object 
    """
    Application Factory Pattern: Instantiates and configures
    the Flask application instance.
    """
    app = Flask(__name__)

    # 2. Configure app settings from environment or defaults
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-12345")



    # Importing here inside the function prevents circular dependency issues
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
