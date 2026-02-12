# Zeabur / Heroku: comando de início (workers=1 para 2GB RAM)
web: gunicorn --workers 1 --threads 2 --timeout 300 --bind 0.0.0.0:$PORT web_server:app
