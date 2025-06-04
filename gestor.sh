#!/bin/bash

APP_DIR="$HOME/web-familiar"
FLASK_LOG="$APP_DIR/logs/flask.log"
NGROK_LOG="$APP_DIR/logs/ngrok.log"
NGROK_TUNNEL_PORT=5000

mkdir -p "$APP_DIR/logs"

start_flask() {
    echo "Iniciando Flask..."
    nohup venv/bin/python3 app.py > "$FLASK_LOG" 2>&1 &
    echo $! > "$APP_DIR/flask.pid"
    echo "Flask iniciado."
}

start_ngrok() {
    echo "Iniciando Ngrok..."
    nohup ngrok http $NGROK_TUNNEL_PORT > "$NGROK_LOG" 2>&1 &
    echo $! > "$APP_DIR/ngrok.pid"
    echo "Ngrok iniciado."
}

stop_flask() {
    if [ -f "$APP_DIR/flask.pid" ]; then
        PID=$(cat "$APP_DIR/flask.pid")
        if ps -p $PID > /dev/null; then
            kill $PID && rm "$APP_DIR/flask.pid"
            echo "Flask detenido."
        else
            echo "Flask no está corriendo."
            rm "$APP_DIR/flask.pid"
        fi
    else
        echo "Flask no está corriendo."
    fi
}

stop_ngrok() {
    if [ -f "$APP_DIR/ngrok.pid" ]; then
        PID=$(cat "$APP_DIR/ngrok.pid")
        if ps -p $PID > /dev/null; then
            kill $PID && rm "$APP_DIR/ngrok.pid"
            echo "Ngrok detenido."
        else
            echo "Ngrok no está corriendo."
            rm "$APP_DIR/ngrok.pid"
        fi
    else
        echo "Ngrok no está corriendo."
    fi
}

status_services() {
    echo "Estado del servidor Flask:"
    if [ -f "$APP_DIR/flask.pid" ] && ps -p $(cat "$APP_DIR/flask.pid") > /dev/null; then
        echo "✅ Flask está corriendo (PID $(cat "$APP_DIR/flask.pid"))"
    else
        echo "❌ Flask no está corriendo"
    fi

    echo "Estado de Ngrok:"
    if [ -f "$APP_DIR/ngrok.pid" ] && ps -p $(cat "$APP_DIR/ngrok.pid") > /dev/null; then
        echo "✅ Ngrok está corriendo (PID $(cat "$APP_DIR/ngrok.pid"))"
    else
        echo "❌ Ngrok no está corriendo"
    fi
}

show_logs() {
    echo -e "\n--- Últimas 50 líneas de Flask ---"
    tail -n 50 "$FLASK_LOG"

    echo -e "\n--- Últimas 50 líneas de Ngrok ---"
    tail -n 50 "$NGROK_LOG"
}

while true; do
    echo -e "\n=== Menú de gestión ==="
    echo "1. Iniciar Flask"
    echo "2. Detener Flask"
    echo "3. Iniciar Ngrok"
    echo "4. Detener Ngrok"
    echo "5. Ver estado"
    echo "6. Ver logs"
    echo "7. Salir"
    read -p "Elige una opción: " opcion

    case $opcion in
        1) start_flask ;;
        2) stop_flask ;;
        3) start_ngrok ;;
        4) stop_ngrok ;;
        5) status_services ;;
        6) show_logs ;;
        7) echo "Saliendo..."; exit 0 ;;
        *) echo "Opción inválida" ;;
    esac
done
