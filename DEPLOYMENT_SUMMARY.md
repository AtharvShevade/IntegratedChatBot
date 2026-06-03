# How to Deploy — AI-Powered SQL Agent Chatbot

> **Version:** 3.0.0 | **Platform:** Ubuntu 22.04 LTS | **Date:** June 3, 2026

---

## Prerequisites

Before deploying, ensure the following are available on the target server:

| Requirement        | Version           | Notes                                  |
|--------------------|-------------------|----------------------------------------|
| Python             | 3.10 or 3.11      | Backend runtime                        |
| Node.js            | 18.x LTS or 20.x  | Frontend build only                    |
| npm                | 9.x+              | Frontend package management            |
| Ollama             | Latest stable     | Local LLM runtime                      |
| Nginx              | 1.24+             | Reverse proxy + static file serving    |
| Oracle DB access   | 19c / 21c         | TCP access on port 1521                |
| Git                | 2.x+              | Source checkout                        |
| Sarvam AI API key  | —                 | Required for speech-to-text only       |

---

## Step 1 — Clone the Repository

```bash
cd /opt
git clone <repository-url> chatbot
cd /opt/chatbot
git checkout <release-tag>
```

---

## Step 2 — Configure Environment Variables

```bash
cp .env.example .env
nano .env
chmod 600 .env
```

Minimum required values in `.env`:

```env
# Oracle Database
ORACLE_HOST=<db-server-ip>
ORACLE_PORT=1521
ORACLE_SERVICE=<service_name>
ORACLE_USER=<db_user>
ORACLE_PASSWORD=<db_password>
ORACLE_MAX_ROWS=100

# LLM (Ollama)
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EXTRACT_MODEL=phi3:mini
OLLAMA_MODEL=mistral:latest
SQL_OLLAMA_MODEL=mistral:latest
OLLAMA_TIMEOUT=180
OLLAMA_EXTRACT_TIMEOUT=30
OLLAMA_KEEP_ALIVE=30m

# Application
CORS_ORIGINS=https://<your-domain.com>
SARVAM_API_KEY=<your_api_key>
XML_USER_PATH=/opt/chatbot/config/XML_User.xml
XML_DEPT_PATH=/opt/chatbot/config/XML_Dept.xml
XML_ROLE_ACCESS_PATH=/opt/chatbot/config/XML_RoleAccess.xml
APP_DB_BASE_PATH=/opt/chatbot/config/
```

---

## Step 3 — Place XML Configuration Files

```bash
mkdir -p /opt/chatbot/config
cp /path/to/XML_User.xml       /opt/chatbot/config/
cp /path/to/XML_Dept.xml       /opt/chatbot/config/
cp /path/to/XML_RoleAccess.xml /opt/chatbot/config/
```

---

## Step 4 — Install Ollama and Pull Models

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull phi3:mini        # ~2 GB — intent extraction
ollama pull mistral:latest   # ~7 GB — SQL generation + chat

# Enable as system service
sudo systemctl enable --now ollama
```

---

## Step 5 — Deploy the Backend

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Build FAISS vector indexes (one-time; re-run when Oracle schema changes)
python backend/sql_agent/main.py

# Create systemd service
sudo tee /etc/systemd/system/chatbot-backend.service > /dev/null <<EOF
[Unit]
Description=AI SQL Agent Chatbot — FastAPI Backend
After=network.target ollama.service

[Service]
User=chatbot
WorkingDirectory=/opt/chatbot
EnvironmentFile=/opt/chatbot/.env
ExecStart=/opt/chatbot/.venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 --port 8001 --workers 2 --log-level info
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now chatbot-backend

# Verify backend is running
curl http://localhost:8001/health
```

---

## Step 6 — Build and Deploy the Frontend

```bash
cd /opt/chatbot/frontend
npm install
npm run build
# Output written to: frontend/dist/
```

---

## Step 7 — Configure Nginx

Create `/etc/nginx/sites-available/chatbot`:

```nginx
server {
    listen 80;
    server_name <your-domain.com>;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name <your-domain.com>;

    ssl_certificate     /etc/ssl/certs/<cert>.pem;
    ssl_certificate_key /etc/ssl/private/<key>.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Serve React SPA
    root /opt/chatbot/frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to FastAPI
    location ~ ^/(chat|compare-execute|guided|reports|speech-to-text|health|download-file) {
        proxy_pass         http://127.0.0.1:8001;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 8 — Verify Deployment

```bash
# Backend health
curl http://localhost:8001/health

# Frontend reachable (expect 200 OK)
curl -I https://<your-domain.com>

# Check all services
sudo systemctl status chatbot-backend
sudo systemctl status ollama
sudo systemctl status nginx
```

---

## Optional — Docker Deployment

```dockerfile
# Dockerfile.backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY sql_agent/ ./sql_agent/
EXPOSE 8001
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
```

```dockerfile
# frontend/Dockerfile.frontend
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

```yaml
# docker-compose.yml
version: "3.9"
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    ports: ["8001:8001"]
    volumes:
      - ./sql_agent/output:/app/sql_agent/output:ro
    depends_on: [ollama]
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    ports: ["80:80", "443:443"]
    depends_on: [backend]
    restart: unless-stopped

  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
    restart: unless-stopped

volumes:
  ollama_data:
```

```bash
# Start services, then pull models
docker compose up -d ollama
docker exec -it $(docker compose ps -q ollama) ollama pull phi3:mini
docker exec -it $(docker compose ps -q ollama) ollama pull mistral:latest
docker compose up -d
```

---

*AI-Powered SQL Agent Chatbot v3.0.0 — iDEAL Report Management Platform*
