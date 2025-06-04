from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from models import User, db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)  # ✅ Permite mantener sesión al cerrar navegador
            flash('Inicio de sesión exitoso 🔐', 'success')
            return redirect(url_for('dashboard'))  # Asegúrate de tener un blueprint llamado 'main' o ajusta
        else:
            flash('Usuario o contraseña incorrectos ❌', 'danger')

    return render_template('login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Por favor, rellena todos los campos ⚠️', 'warning')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Ese usuario ya existe 🚫', 'warning')
            return redirect(url_for('auth.register'))

        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user, remember=True)
        flash('Registro exitoso 🎉 Bienvenido/a', 'success')
        return redirect(url_for('dashboard'))  # Ajusta si tu dashboard está en otro blueprint

    return render_template('register.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión 👋', 'info')
    return redirect(url_for('auth.login'))
