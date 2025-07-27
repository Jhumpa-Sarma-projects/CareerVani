from . import db
from flask_login import UserMixin
from . import login_manager
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

    # Optional: if you want reverse access to user.speech_feedback
    feedback = db.relationship('SpeechFeedback', backref='user', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SpeechFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transcript = db.Column(db.Text, nullable=False)
    grammar_issues = db.Column(db.Text)
    pron_score = db.Column(db.Integer)
    badge = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
