# IPAM: Zero-Touch Enterprise IP Address Management

IPAM is a modern, responsive, and automated IP Address Management system designed to be "zero-touch" out of the box while providing the flexibility required for enterprise environments.

---

## ✨ Features

- **Zero-Touch Setup** — An embedded Setup Wizard handles database migrations, initial admin creation, and configuration via the UI.
- **Automated Discovery** — Optional background workers (Celery) scan subnets using ICMP/SNMPv3 to find active hosts and flag conflicts.
- **Multi-Vendor Integrations** — Pull live network data directly from your infrastructure platforms (see below).
- **Role-Based Access Control** — Strict separation between `admin` and `readonly` users, with full OIDC Single Sign-On (SSO) support.
- **IPv6 Ready** — Full support for IPv4 and IPv6 address management with protocol-agnostic networking logic.
- **Approval Queue** — Subnets discovered by integrations can be reviewed and approved by admins before creation.
- **CSV Import/Export** — Bulk import and export subnet data via CSV files.

---

## 🔌 Supported Integrations

IPAM includes a pluggable multi-vendor integration framework that connects directly to your network infrastructure to automatically discover subnets, enrich IP address records, and inventory managed devices.

| Vendor | Adapter | Auth Methods | Data Collected |
|--------|---------|-------------|----------------|
| 🌐 **Cisco Meraki** | Official `meraki` SDK | API Key | VLANs, clients, device inventory |
| 🛡️ **Fortinet FortiGate** | FortiOS REST API | API Token **or** Username/Password | Interfaces, DHCP leases, ARP table |
| 📡 **HPE Aruba Central** | `pycentral` SDK | Client ID + Secret | Groups/VLANs, wireless + wired clients, APs, switches, gateways |
| 🔥 **Palo Alto Networks** | PAN-OS XML API | API Key **or** Username/Password | Interfaces, ARP table, DHCP leases, system info |

### How It Works

1. **Configure** — Add your vendor credentials through the Integrations UI. All API keys and passwords are encrypted at rest using Fernet symmetric encryption.
2. **Sync** — Trigger a manual sync or let the background scheduler (every 30 minutes) pull data automatically.
3. **Enrich** — Vendor data fills in missing fields (MAC, hostname, OS, device type) on your existing IP records without overwriting human-entered data.
4. **Discover** — New subnets found by vendors are either auto-created or routed to the **Approval Queue** for admin review, based on a per-provider toggle.

---

## Architecture

IPAM is built with a strict Separation of Concerns (SoC) architecture:
- **API Routers**: Handle HTTP request/response formatting (`app/api/v1/`).
- **Service Layer**: Contains all core business logic and validation (`app/services/`).
- **Adapter Layer**: Pluggable vendor integrations via abstract base class (`app/integrations/`).
- **Data Models**: Defines SQLAlchemy ORM models (`app/models/`).
- **Background Workers**: Celery tasks for network sweeps and vendor sync (`app/worker/`).

---

## Quick Start (Docker)

The fastest way to run IPAM is using Docker Compose. This starts the core application (Frontend, Backend, Database, and Redis).

1. **Clone the repository**:
   ```bash
   git clone https://github.com/allo28734/ipam.git
   cd ipam
   ```

2. **Initialize Environment** (one-time):
   Run the bootstrap script to generate a `.env` file with secure random passwords and encryption keys:
   ```bash
   # Linux / macOS
   chmod +x init.sh && ./init.sh

   # Windows (PowerShell)
   .\init.ps1
   ```
   > **Note:** The script is safe to re-run — it will not overwrite an existing `.env` file. Generated credentials are printed once to the console; save them if needed for external database access.

3. **Start the Application**:
   ```bash
   docker compose up -d
   ```

4. **Initialize IPAM**:
   Visit `http://<your-server-ip>` in your browser and complete the Setup Wizard to create your first admin account.

---

## Enabling Network Discovery (Background Scanning)

To save system resources (RAM/CPU), background network scanning is disabled by default. If you want the system to automatically sweep your subnets for active devices, you must start Docker Compose with the `discovery` profile:

```bash
docker compose --profile discovery up -d
```
*Note: You can configure the frequency and methods (ICMP, SNMP) of these scans from the IPAM Settings menu.*

---

## Production Deployment

### 1. Reverse Proxy & HTTPS
**IMPORTANT**: The built-in Nginx container serves the frontend over **Plain HTTP on port 80**.
For production use, you **MUST** place IPAM behind a reverse proxy to handle SSL/TLS termination.

This requires two things:
- **A TLS certificate** — Obtained from your organization's Certificate Authority (e.g., DigiCert, GoDaddy, an internal CA).
- **A reverse proxy** — A web server on the host that terminates TLS and forwards traffic to the Docker container.

#### Option A: Nginx (Recommended for Enterprise)

Use this option when your institution provides TLS certificates through a CA like DigiCert, GoDaddy, Sectigo, or an internal PKI.

1. **Obtain a TLS certificate** from your institution's certificate provider. You will receive a certificate file (`.crt` or `.pem`) and a private key file (`.key`).

2. **Install Nginx** on the host (Ubuntu/Debian):
   ```bash
   sudo apt update && sudo apt install nginx -y
   ```

3. **Copy your certificate files** to the server:
   ```bash
   sudo cp ipam.crt /etc/ssl/certs/ipam.crt
   sudo cp ipam.key /etc/ssl/private/ipam.key
   sudo chmod 600 /etc/ssl/private/ipam.key
   ```

4. **Create the Nginx site configuration** at `/etc/nginx/sites-available/ipam`:
   ```nginx
   # Redirect HTTP to HTTPS
   server {
       listen 80;
       server_name ipam.example.com;
       return 301 https://$host$request_uri;
   }

   # HTTPS reverse proxy
   server {
       listen 443 ssl;
       server_name ipam.example.com;

       ssl_certificate     /etc/ssl/certs/ipam.crt;
       ssl_certificate_key /etc/ssl/private/ipam.key;

       # Modern TLS settings
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_prefer_server_ciphers on;

       location / {
           proxy_pass http://127.0.0.1:80;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
   > **Note:** Replace `ipam.example.com` with your actual FQDN.

5. **Enable the site and restart Nginx**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/ipam /etc/nginx/sites-enabled/
   sudo nginx -t          # Verify configuration
   sudo systemctl restart nginx
   ```

6. **Update the frontend port binding** in `docker-compose.yml` to bind only to localhost, preventing direct access that bypasses TLS:
   ```yaml
   ports:
     - "127.0.0.1:80:80"    # Only accessible via the host reverse proxy
   ```

#### Option B: Caddy (Automatic Let's Encrypt)

If your environment allows outbound ACME challenges, [Caddy](https://caddyserver.com/) is the simplest option — it provisions and renews HTTPS certificates automatically via Let's Encrypt with zero configuration.

1. Create a `Caddyfile` in your project root:
   ```caddyfile
   # Replace ipam.example.com with your actual domain.
   ipam.example.com {
       reverse_proxy ipam_frontend:80
   }
   ```

2. Add Caddy as a service to your `docker-compose.yml` (or run it standalone):
   ```yaml
   caddy:
     image: caddy:alpine
     container_name: ipam_caddy
     restart: unless-stopped
     ports:
       - "443:443"
       - "80:80"     # Required for ACME HTTP-01 challenge
     volumes:
       - ./Caddyfile:/etc/caddy/Caddyfile
       - caddy_data:/data
     depends_on:
       - frontend
     logging:
       driver: json-file
       options:
         max-size: "50m"
         max-file: "5"
   ```
   > **Note:** If you add Caddy to the compose stack, remove `ports: - "80:80"` from the `frontend` service to avoid a port conflict.

3. Add `caddy_data` to the `volumes:` section at the bottom of your `docker-compose.yml`, then bring everything up:
   ```bash
   docker compose up -d
   ```
   Caddy will automatically obtain a TLS certificate for your domain on first request.

### 2. Bring Your Own Database (BYOD)
By default, the `docker-compose.yml` spins up embedded PostgreSQL and Redis containers. If you have a dedicated database cluster:
1. Open your `.env` file.
2. Uncomment and define the `EXTERNAL_DB_URL` and `EXTERNAL_REDIS_URL` variables.
3. (Optional) Comment out the `db` and `redis` service blocks in `docker-compose.yml`.
4. Run `docker compose up -d`.

### 3. Application Secrets
If you used the `init.sh` / `init.ps1` bootstrap scripts, all secrets (`DB_PASSWORD`, `REDIS_PASSWORD`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`) were generated automatically. No manual action is needed.

If you created `.env` manually, ensure you generate cryptographically strong values:
```bash
# Generate a JWT Secret Key
python -c "import secrets; print(secrets.token_hex(32))"

# Generate an Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Troubleshooting

- **First boot secrets**: The Docker entrypoint will automatically generate `JWT_SECRET_KEY` and `ENCRYPTION_KEY` on first boot and save them to `backend_data/app_secrets.env`.
- **Database migrations**: If the database schema is outdated, run `docker compose exec backend alembic upgrade head`.
- **CORS errors in local development**: Set `CORS_ORIGINS=http://localhost:5173` in your `.env` file. In Docker production, CORS is not needed (Nginx proxies API requests internally).
- **Discovery offline warning**: If you see a "Discovery Offline" banner, start Docker with `docker compose --profile discovery up -d` to activate background scanning workers.

---

## Local Development Setup

If you wish to contribute or modify the code locally without Docker, please see the specific README files in the respective directories:
- **[Backend Setup & API](backend/README.md)**
- **[Frontend Setup & UI](frontend/README.md)**

Alternatively, you can run the provided helper scripts (`start.bat` on Windows or `start.ps1` for PowerShell) to quickly spin up the local development servers.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19 + Vite, Tailwind CSS v4 |
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Database** | PostgreSQL (asyncpg) |
| **Background** | Celery + Redis |
| **Auth** | JWT (OAuth2), OIDC SSO, RBAC |
| **Encryption** | Fernet (cryptography) |
| **Discovery** | ICMP, SNMPv3, Nmap |
| **Integrations** | Meraki SDK, pycentral, httpx, PAN-OS XML |

---

## License

This project is open source. See the [LICENSE](LICENSE) file for details.
