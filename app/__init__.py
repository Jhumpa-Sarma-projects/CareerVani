from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    mail.init_app(app)

    # Save reference to mail inside extensions for use in routes
    app.extensions['mail'] = mail

    # Register blueprints
    from .routes import main
    from .auth import auth

    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app
