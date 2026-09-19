PYTEST := .venv/bin/python -m pytest
PYTHON := .venv/bin/python
UVICORN := .venv/bin/uvicorn
PID_BE := .pids/backend.pid

.PHONY: help install test ingest ingest-sample buscar verificar-fase1 dev-be dev stop status deploy install-services install-cloudflared clean

help:
	@printf "\nPictoHistorias — comandos (fase 1)\n\n"
	@printf "  make install          Instala dependencias en .venv\n"
	@printf "  make test             Corre los tests\n"
	@printf "  make ingest-sample    Ingesta de prueba (--limit 50)\n"
	@printf "  make ingest           Ingesta completa del catalogo ARASAAC\n"
	@printf "  make buscar q=\"coche de mama\"   Busca pictos para un concepto\n"
	@printf "  make verificar-fase1  Corre los 20 conceptos de prueba de las historias de ejemplo\n"
	@printf "  make dev-be            Arranca el backend FastAPI en :8002 con --reload\n"
	@printf "  make dev              Arranca la app completa (backend + frontend estático) en background\n"
	@printf "  make stop             Para el backend arrancado con make dev\n"
	@printf "  make status           Muestra si el backend está corriendo\n"
	@printf "  make deploy           Instala/recarga la config nginx en producción (sudo)\n"
	@printf "  make install-services Instala y arranca el servicio systemd del backend (sudo)\n"
	@printf "  make install-cloudflared Instala cloudflared y lo registra como servicio systemd (sudo)\n"
	@printf "  make clean            Borra __pycache__ y .pytest_cache (no toca cache/, es el snapshot de ARASAAC)\n\n"

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	$(PYTEST) tests/ -v

ingest-sample:
	$(PYTHON) -m scripts.ingest_arasaac --limit 50

ingest:
	$(PYTHON) -m scripts.ingest_arasaac

buscar:
	$(PYTHON) -m scripts.buscar_picto "$(q)"

verificar-fase1:
	$(PYTHON) -m scripts.verificar_fase1

dev-be:
	$(UVICORN) backend.main:app --host 127.0.0.1 --port 8002 --reload

dev: .pids
	$(UVICORN) backend.main:app --host 127.0.0.1 --port 8002 --reload > logs/backend.log 2>&1 & echo $$! > $(PID_BE)
	@echo "App completa (backend + frontend estático) → http://127.0.0.1:8002/  (PID $$(cat $(PID_BE)))"

stop:
	@if [ -f $(PID_BE) ]; then \
	  pid=$$(cat $(PID_BE)); \
	  kill $$pid 2>/dev/null && echo "Backend parado (PID $$pid)" || echo "Backend: proceso $$pid ya no existía"; \
	  rm -f $(PID_BE); \
	else echo "Backend: no hay PID guardado"; fi

status:
	@printf "  Backend (8002): "
	@if [ -f $(PID_BE) ] && kill -0 $$(cat $(PID_BE)) 2>/dev/null; \
	  then echo "✓ corriendo (PID $$(cat $(PID_BE)))"; \
	  else echo "✗ parado"; fi

deploy:
	@echo "Instalando config nginx..."
	sed "s/TAILSCALE_IP/$$(tailscale ip -4)/" nginx-pictohistorias.conf | sudo tee /etc/nginx/sites-available/pictohistorias > /dev/null
	sudo ln -sf /etc/nginx/sites-available/pictohistorias /etc/nginx/sites-enabled/pictohistorias
	sudo nginx -t && sudo systemctl reload nginx
	@echo "✓ PictoHistorias en producción → http://$$(tailscale ip -4):5252 (Tailscale)"

install-services:
	sudo cp pictohistorias-backend.service /etc/systemd/system/pictohistorias-backend.service
	sudo systemctl daemon-reload
	sudo systemctl enable pictohistorias-backend
	sudo systemctl start pictohistorias-backend
	@echo "✓ Servicio instalado — systemctl status pictohistorias-backend"
	@echo "  Logs → journalctl -u pictohistorias-backend -f"

install-cloudflared:
	@echo "Instalando cloudflared..."
	curl -L --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
	sudo dpkg -i /tmp/cloudflared.deb
	rm /tmp/cloudflared.deb
	sudo cloudflared service install $$(grep '^CLOUDFLARE_TUNNEL_TOKEN=' .env | cut -d= -f2-)
	sudo systemctl status cloudflared --no-pager
	@echo "✓ cloudflared instalado — systemctl status cloudflared"

.pids:
	@mkdir -p .pids logs

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf .pytest_cache
