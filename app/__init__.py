from flask import Flask, Blueprint
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_restplus import Api
from flask_qrcode import QRcode

app = Flask(__name__)
app.config.from_object(Config)
login = LoginManager(app)
QRcode(app)
from app import routes, models
from app.dash import dash
from app.farer import farer
from app.events import events
from app.pay import pay

app.register_blueprint(dash, url_prefix='/dash')
app.register_blueprint(farer, url_prefix='/farer')
app.register_blueprint(events, url_prefix='/events')
app.register_blueprint(pay, url_prefix='/pay')
