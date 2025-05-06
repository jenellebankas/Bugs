from flask import Flask, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babel import Babel
from flask_admin import Admin
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_mailman import Mail



app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
bcrypt=Bcrypt(app)


def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'en')

# login manager
login_manager = LoginManager()
login_manager.init_app(app)

# admin
admin = Admin(app, template_mode='bootstrap4')

# babel
babel = Babel(app, locale_selector=get_locale)

# debug (logging)
import logging
logging.basicConfig(level=logging.DEBUG)

# migrations in db 
migrate = Migrate(app, db, render_as_batch=True)

#CSRF Token
csrf = CSRFProtect(app)

#Mailman
mail = Mail()
mail.init_app(app)

from app import views, models


