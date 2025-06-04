from app import app, db
from models import TaskTemplate

def init_tasks():
    TaskTemplate.query.delete()
    db.session.commit()

    tareas = [
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

    for t in tareas:
        task = TaskTemplate(description=t["description"], reward_value=t["reward_value"])
        db.session.add(task)

    db.session.commit()
    print("Tareas inicializadas.")

if __name__ == "__main__":
    with app.app_context():
        init_tasks()
