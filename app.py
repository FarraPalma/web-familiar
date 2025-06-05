from flask import Flask, redirect, url_for, render_template, request, jsonify, flash
from flask_login import LoginManager, login_required, current_user
from models import db, User, ShoppingItem, Task, Reward, ClaimedReward, CoinTransaction, TaskTemplate, MonthlyIncome, Expense, Note
from auth import auth
import os
from datetime import datetime, date
from sqlalchemy import func, extract

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mi_clave_secreta'

# Crear carpeta 'instance' para la base de datos si no existe
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

db_path = os.path.join(instance_path, 'db.sqlite3')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar base de datos
db.init_app(app)

# Configurar Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registrar blueprint de autenticación
app.register_blueprint(auth)

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    else:
        return redirect(url_for("auth.login"))

@app.route("/dashboard")
@login_required
def dashboard():
    # Buscar notas para hoy
    hoy = date.today()
    notas_hoy = Note.query.filter(
        func.date(Note.start) == hoy
    ).all()
    return render_template("dashboard.html", user=current_user, notas_hoy=notas_hoy)

@app.route("/bienestar")
@login_required
def bienestar():
    return render_template("bienestar.html", user=current_user)

@app.route("/lista-compra", methods=['GET', 'POST'])
@login_required
def lista_compra():
    if request.method == 'POST':
        item_name = request.form.get('item')
        if item_name:
            nuevo_item = ShoppingItem(name=item_name, added_by=current_user.username)
            db.session.add(nuevo_item)
            db.session.commit()

    items = ShoppingItem.query.all()
    status_order = {'pronto': 0, 'faltante': 1, 'comprado': 2}
    items.sort(key=lambda item: (status_order.get(item.status, 3), item.name.lower()))
    return render_template("lista_compra.html", items=items, user=current_user)

@app.route('/add-item', methods=['POST'])
@login_required
def add_item():
    name = request.form.get('name')
    if name:
        new_item = ShoppingItem(name=name, added_by=current_user.username)
        db.session.add(new_item)
        db.session.commit()
    return redirect(url_for('lista_compra'))

@app.route('/toggle-item/<int:item_id>', methods=['POST'])
@login_required
def toggle_item(item_id):
    item = ShoppingItem.query.get_or_404(item_id)
    if item.status == 'faltante':
        item.status = 'pronto'
    elif item.status == 'pronto':
        item.status = 'comprado'
    else:
        item.status = 'faltante'
    db.session.commit()
    return jsonify({'status': item.status})

# --- NUEVO: Función para sincronizar tareas diarias desde plantilla ---
def sync_daily_tasks_for_user(user):
    hoy = date.today()
    plantillas = TaskTemplate.query.all()
    for plantilla in plantillas:
        existe = Task.query.filter_by(user_id=user.id, description=plantilla.description, date=hoy).first()
        if not existe:
            tarea = Task(
                user_id=user.id,
                description=plantilla.description,
                reward_value=plantilla.reward_value,
                date=hoy,
                completed=False
            )
            db.session.add(tarea)
    db.session.commit()

@app.route("/añadir-tarea", methods=["GET", "POST"])
@login_required
def añadir_tarea():
    sync_daily_tasks_for_user(current_user)  # Para asegurarnos tareas diarias existen para usuario

    if request.method == "POST":
        desc = request.form.get("description")
        if desc:
            tarea_existente = Task.query.filter_by(user_id=current_user.id, description=desc, completed=False, date=date.today()).first()
            if not tarea_existente:
                plantilla = TaskTemplate.query.filter_by(description=desc).first()
                if plantilla:
                    nueva = Task(
                        user_id=current_user.id,
                        description=desc,
                        reward_value=plantilla.reward_value,
                        date=date.today(),
                        completed=False
                    )
                    db.session.add(nueva)
                    db.session.commit()
            return redirect(url_for("añadir_tarea"))

    hoy = date.today()
    plantillas = TaskTemplate.query.all()

    tareas_estado = []
    for plantilla in plantillas:
        tarea_usuario = Task.query.filter_by(user_id=current_user.id, description=plantilla.description, date=hoy).first()
        tareas_estado.append({
            'description': plantilla.description,
            'reward_value': plantilla.reward_value,
            'completed': tarea_usuario.completed if tarea_usuario else False,
            'task_id': tarea_usuario.id if tarea_usuario else None
        })

    return render_template("añadir_tarea.html", user=current_user, tareas_estado=tareas_estado)

@app.route('/crear-tarea-usuario', methods=['POST'])
@login_required
def crear_tarea_usuario():
    data = request.get_json()
    descripcion = data.get('description')
    if not descripcion:
        return jsonify({'error': 'Descripción no proporcionada'}), 400

    hoy = date.today()
    tarea_existente = Task.query.filter_by(user_id=current_user.id, description=descripcion, date=hoy).first()
    if tarea_existente:
        return jsonify({'success': True, 'task_id': tarea_existente.id})

    plantilla = TaskTemplate.query.filter_by(description=descripcion).first()
    if not plantilla:
        return jsonify({'error': 'Plantilla de tarea no encontrada'}), 404

    nueva_tarea = Task(
        user_id=current_user.id,
        description=descripcion,
        reward_value=plantilla.reward_value,
        date=hoy,
        completed=False
    )
    db.session.add(nueva_tarea)
    db.session.commit()

    return jsonify({'success': True, 'task_id': nueva_tarea.id})

@app.route("/marcar-tarea/<int:task_id>", methods=["POST"])
@login_required
def marcar_tarea(task_id):
    tarea = Task.query.get_or_404(task_id)
    if tarea.user_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403
    if tarea.completed:
        return jsonify({'error': 'Tarea ya completada'}), 400

    tarea.completed = True
    current_user.coins = (current_user.coins or 0) + tarea.reward_value
    db.session.add(CoinTransaction(user_id=current_user.id, amount=tarea.reward_value, reason=tarea.description))
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'task_id': tarea.id,
            'new_coins': current_user.coins,
            'reward_value': tarea.reward_value,
            'message': f'Tarea "{tarea.description}" marcada como completada. +{tarea.reward_value} monedas.'
        })
    else:
        return redirect(url_for("añadir_tarea"))

@app.route("/ranking")
@login_required
def ranking():
    # Obtener ranking total: usuarios con el total de tareas completadas
    ranking_total = (
        db.session.query(User, func.count(Task.id).label("total"))
        .join(Task, (Task.user_id == User.id) & (Task.completed == True))
        .group_by(User.id)
        .order_by(func.count(Task.id).desc())
        .all()
    )

    # Preparar ranking de tareas más realizadas por usuario
    ranking_tareas_usuario = {}
    for user, _ in ranking_total:
        tareas_completadas = (
            db.session.query(Task.description, func.count(Task.id).label("veces"))
            .filter(Task.user_id == user.id, Task.completed == True)
            .group_by(Task.description)
            .order_by(func.count(Task.id).desc())
            .all()
        )
        ranking_tareas_usuario[user.id] = {
            "username": user.username,
            "tareas": tareas_completadas,
        }

    return render_template("ranking.html", ranking_total=ranking_total, ranking_tareas_usuario=ranking_tareas_usuario)

@app.route("/recompensas")
@login_required
def recompensas():
    recompensas_disponibles = Reward.query.all()
    return render_template("recompensas.html", recompensas=recompensas_disponibles, user=current_user)

@app.route("/canjear-recompensa/<int:reward_id>", methods=["POST"])
@login_required
def canjear_recompensa(reward_id):
    recompensa = Reward.query.get_or_404(reward_id)
    if current_user.coins >= recompensa.cost:
        current_user.coins -= recompensa.cost
        db.session.add(ClaimedReward(user_id=current_user.id, reward_id=recompensa.id))
        db.session.add(CoinTransaction(user_id=current_user.id, amount=-recompensa.cost, reason=f"Canjeó: {recompensa.name}"))
        db.session.commit()
        flash(f'Has canjeado: {recompensa.name} por {recompensa.cost} monedas.', 'success')
    else:
        flash('No tienes suficientes monedas para esta recompensa.', 'danger')
    return redirect(url_for("recompensas"))

@app.route("/monedas")
@login_required
def monedas():
    saldo = current_user.coins or 0
    transacciones = CoinTransaction.query.filter_by(user_id=current_user.id).order_by(CoinTransaction.timestamp.desc()).all()

    # Obtener ranking de tareas más realizadas por usuario
    ranking_total = (
        db.session.query(User, func.count(Task.id).label("total"))
        .join(Task, (Task.user_id == User.id) & (Task.completed == True))
        .group_by(User.id)
        .order_by(func.count(Task.id).desc())
        .all()
    )

    ranking_tareas_usuario = {}
    for user, _ in ranking_total:
        tareas_completadas = (
            db.session.query(Task.description, func.count(Task.id).label("veces"))
            .filter(Task.user_id == user.id, Task.completed == True)
            .group_by(Task.description)
            .order_by(func.count(Task.id).desc())
            .all()
        )
        ranking_tareas_usuario[user.id] = {
            "username": user.username,
            "tareas": tareas_completadas,
        }

    return render_template(
        "monedas.html",
        user=current_user,
        saldo=saldo,
        transacciones=transacciones,
        ranking_tareas_usuario=ranking_tareas_usuario
    )

@app.route("/calendario")
@login_required
def calendario_tareas():
    return render_template("calendario_tareas.html", user=current_user)

@app.route("/facturas", methods=["GET", "POST"])
@login_required
def facturas():
    hoy = date.today()
    mes_actual = hoy.strftime("%Y-%m")

    if request.method == "POST":
        tipo = request.form.get("tipo")
        monto = float(request.form.get("monto"))
        descripcion = request.form.get("descripcion")
        compartido = request.form.get("compartido", "")
        
        nuevo = Expense(
            user_id=current_user.id,
            amount=monto,
            description=descripcion,
            is_fixed=(tipo == "fijo"),
            shared_between=compartido,
            date=date.today()
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("facturas"))

    # Ingresos del mes (de todos los usuarios)
    ingresos_mes = MonthlyIncome.query.filter_by(month=mes_actual).all()
    total_base_salary = sum(i.base_salary for i in ingresos_mes)
    total_extra_income = sum(i.extra_income for i in ingresos_mes)
    total_ingresos = total_base_salary + total_extra_income

    # Ingreso individual del usuario actual
    ingreso_usuario = MonthlyIncome.query.filter_by(user_id=current_user.id, month=mes_actual).first()
    if not ingreso_usuario:
        ingreso_usuario = MonthlyIncome(user_id=current_user.id, month=mes_actual, base_salary=getattr(current_user, 'salary', 0) or 0, extra_income=0)
        db.session.add(ingreso_usuario)
        db.session.commit()

    # Gastos del mes (todos los usuarios)
    gastos_mes = Expense.query.filter(
        extract('year', Expense.date) == hoy.year,
        extract('month', Expense.date) == hoy.month
    ).all()

    total_fijos = sum(g.amount for g in gastos_mes if g.is_fixed)
    total_variables = sum(g.amount for g in gastos_mes if not g.is_fixed)

    balance = total_ingresos - (total_fijos + total_variables)

    return render_template(
        "facturas.html",
        gastos=gastos_mes,
        total_fijos=total_fijos,
        total_variables=total_variables,
        ingresos={"base_salary": total_base_salary, "extra_income": total_extra_income, "month": mes_actual},
        ingreso_usuario=ingreso_usuario,
        balance=balance,
        user=current_user
    )
@app.route("/actualizar_ingresos", methods=["POST"])
@login_required
def actualizar_ingresos():
    mes = request.form.get("mes")
    base = float(request.form.get("base_salary", 0))
    extra = float(request.form.get("extra_income", 0))

    ingresos = MonthlyIncome.query.filter_by(user_id=current_user.id, month=mes).first()
    if ingresos:
        ingresos.base_salary = base
        ingresos.extra_income = extra
    else:
        ingresos = MonthlyIncome(user_id=current_user.id, month=mes, base_salary=base, extra_income=extra)
        db.session.add(ingresos)

    db.session.commit()
    return redirect(url_for("facturas"))

@app.route("/notas")
@login_required
def notas():
    notas = Note.query.order_by(Note.start).all()
    # Convertir a lista de dicts para el calendario (evita pasar métodos a Jinja)
    notas_eventos = [n.to_event_dict() for n in notas]
    return render_template("notas.html", user=current_user, notas=notas, notas_eventos=notas_eventos)

@app.route("/agregar-nota", methods=["POST"])
@login_required
def agregar_nota():
    title = request.form.get("title")
    content = request.form.get("content")
    start = request.form.get("start")
    end = request.form.get("end")
    if title and content and start:
        note = Note(
            title=title,
            content=content,
            start=datetime.strptime(start, "%Y-%m-%dT%H:%M"),
            end=datetime.strptime(end, "%Y-%m-%dT%H:%M") if end else None,
            user_id=current_user.id
        )
        db.session.add(note)
        db.session.commit()
    return redirect(url_for("notas"))

@app.route("/seguimiento-entrenamientos")
@login_required
def seguimiento_entrenamientos():
    return "<h2>Seguimiento de entrenamientos (en construcción)</h2>"

@app.route("/registro-alimentacion")
@login_required
def registro_alimentacion():
    return "<h2>Registro de alimentación (en construcción)</h2>"

@app.route("/estadisticas")
@login_required
def estadisticas():
    return "<h2>Estadísticas por usuario (en construcción)</h2>"

# --- MOSTRAR MONEDAS EN TODAS LAS PLANTILLAS ---
@app.context_processor
def inject_monedas_usuario():
    if current_user.is_authenticated:
        return dict(monedas_usuario=current_user.coins or 0)
    return dict(monedas_usuario=0)

# Inicializar base y cargar datos
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Asegurar que todos los usuarios tengan el campo 'coins'
        for user in User.query.all():
            if user.coins is None:
                user.coins = 0
        db.session.commit()

        # Inicializar la lista de compra si está vacía
        if not ShoppingItem.query.first():
            productos_iniciales = [
                "Zanahoria ensalada", "Frutos secos (pistachos…)", "Salsas lights (ketchup)", "Fideos chinos",
                "Lejia", "Perfumador ropa", "Queso en lonchas", "Cafe", "Especies (ajo)", "Churrasco de pollo",
                "Pimiento tricolor", "Caldo de pollo", "Ensaladas", "Pescado(sepia, merluza, gambas congeladas)",
                "Kebab de pollo", "Huevos", "Pechuga de pavo", "Queso fresco", "Fruta (kiwi)", "Nestea cero mango",
                "Queso fresco batido", "Aceite de oliva", "Agua", "Vinagre", "Sal", "Pan", "Pasta spaghetti",
                "Setas congeladas", "Salchichas de pavo", "Leche evaporada", "Pechuga de pavo en tubo",
                "Queso parmesano", "Detergente", "Cebolla Natural", "Servilletas", "Papel higiénico", "Champú",
                "Gel", "Papel de horno", "Ambientador lavavajillas", "Papel de plata", "Toallitas", "Mantel", "Atun",
                "Champiñones", "Pastillas lavavajillas", "Patatas", "Tomate natural", "Fly de bichos",
                "Bote para la sal del lavavajillas", "Corta uñas", "Pinza de depilar", "Colonia", "Cuchilla",
                "Polvos para ropa de color", "Aceite girasol", "Cocacola zero", "Leche", "Desinfectante ropa",
                "Hamburguesas", "Pan hamburguesas", "Berenjena", "Carne picada", "Tomate", "Queso Mozarella",
                "Puerros", "Nuez moscada", "Picos"
            ]
            for nombre in productos_iniciales:
                db.session.add(ShoppingItem(name=nombre, added_by="Sistema"))
            db.session.commit()

        # Inicializar recompensas si no existen
        recompensas_iniciales = [
            ("Salir Cerve 🍻", 25),
            ("Salir cenar/almorzar 🍽️", 60),
            ("Pedir a medias 🍕", 50),
            ("Elijo peli 100% 🎬", 30),
            ("Elijo serie 100% 📺", 30),
            ("Cosquillitas 🤭", 15),
            ("2h PC 🖥️", 40),
            ("Masaje 💆", 40),
            ("Elegir día juntos 100% 📅", 100),
            ("Invitas tu 1 cosa 🥤", 80),
            ("Elijo plan 🗺️", 70),
            ("Voy por monster 🥤", 10),
            ("Me libro 1 cosa 📚", 90),
        ]

        for nombre, coste in recompensas_iniciales:
            existe = Reward.query.filter_by(name=nombre).first()
            if not existe:
                nueva_recompensa = Reward(name=nombre, cost=coste)
                db.session.add(nueva_recompensa)
        db.session.commit()

        # Inicializar plantillas de tareas si no existen
        if not TaskTemplate.query.first():
            tareas_iniciales = [
                {"description": "Limpiar suelos, superficies y cristales", "reward_value": 9},
                {"description": "Cocinar las comidas diarias", "reward_value": 3},
                {"description": "Lavar los platos", "reward_value": 4},
                {"description": "Hacer la colada", "reward_value": 3},
                {"description": "Planchar la ropa", "reward_value": 7},
                {"description": "Limpiar el baño", "reward_value": 7},
                {"description": "Hacer las camas y cambiar la ropa de cama", "reward_value": 6},
                {"description": "Hacer la compra y reponer la despensa", "reward_value": 3},
                {"description": "Organizar y ordenar los espacios", "reward_value": 7},
                {"description": "Realizar pequeñas reparaciones y mantenimiento", "reward_value": 4},
                {"description": "Sacar a la perra, darle de comer y bañarla", "reward_value": 7},
            ]

            for tarea in tareas_iniciales:
                nueva_tarea = TaskTemplate(description=tarea["description"], reward_value=tarea["reward_value"])
                db.session.add(nueva_tarea)
            db.session.commit()
    app.run(debug=True, host="0.0.0.0")
