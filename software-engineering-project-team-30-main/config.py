WTF_CSRF_ENABLED = True
SECRET_KEY = 'backend-dev-babes'

import os
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = True

RESET_PASS_TOKEN_MAX_AGE = 3600  

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = 'skrrrtlimited@gmail.com'
MAIL_PASSWORD = 'ixho lqpx jskn ekxf'
DEFAULT_MAIL_SENDER = ('SKRRT Password Reset', 'skrrrtlimited@gmail.com')

gmaps = "GMAPS"
