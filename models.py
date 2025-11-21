from extensions import db
from flask_login import UserMixin
from datetime import date

class User(UserMixin, db.Model):                     # Model for storing user data
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Task(db.Model):                                 # Model for storing the details of task added
    id = db.Column(db.Integer, primary_key=True)
    task_text = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.Date, default=date.today)   
    status = db.Column(db.String(20), default="pending")   # pending by default
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # id of user who added the task
