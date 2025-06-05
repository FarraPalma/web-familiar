from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    coins = db.Column(db.Integer, default=0)  # Monedas acumuladas por el usuario
    salary = db.Column(db.Float, default=0)  # Salario base del usuario

    # Relaciones
    tasks = relationship('Task', backref='user', lazy=True)
    coin_transactions = relationship('CoinTransaction', backref='user', lazy=True)
    claimed_rewards = relationship('ClaimedReward', backref='user', lazy=True)
    notes = relationship('Note', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class ShoppingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    added_by = db.Column(db.String(100))
    status = db.Column(db.String(20), default='faltante')  # 'faltante', 'pronto', 'comprado'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Item {self.name} - {self.status}>'

class TaskTemplate(db.Model):
    __tablename__ = 'task_template'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), unique=True, nullable=False)
    reward_value = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<TaskTemplate {self.description} ({self.reward_value} coins)>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, default=date.today)
    completed = db.Column(db.Boolean, default=False)
    reward_value = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class CoinTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Puede ser positivo (recompensa) o negativo (gasto)
    reason = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    cost = db.Column(db.Integer, nullable=False)  # Costo en monedas
    claimed = relationship('ClaimedReward', backref='reward', lazy=True)

class ClaimedReward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reward_id = db.Column(db.Integer, db.ForeignKey('reward.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class MonthlyIncome(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    month = db.Column(db.String(7))  # Ej: "2025-05"
    base_salary = db.Column(db.Float, nullable=False, default=0)
    extra_income = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    is_fixed = db.Column(db.Boolean, default=False)
    shared_between = db.Column(db.String(255))  # Por ahora puede ser una lista de nombres separada por comas
    date = db.Column(db.Date, default=datetime.utcnow)

    def month(self):
        return self.date.strftime("%Y-%m")

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    start = db.Column(db.DateTime, nullable=False)  # Fecha y hora de inicio
    end = db.Column(db.DateTime, nullable=True)     # Fecha y hora de fin (opcional)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Note {self.title}>'

    def to_event_dict(self):
        return {
            "title": f"{self.title} ({self.user.username})",
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "description": self.content
        }