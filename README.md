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
   git clone https://github.com/ipam-project/IPAM.git
   cd IPAM
   ```

2. **Configure Environment Variables**:
   Copy the example environment file and update the `CHANGE_ME` values with secure passwords/keys.
   ```bash
   cp .env.example .env
   ```

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

The easiest option is [Caddy](https://caddyserver.com/), which provisions and renews HTTPS certificates automatically via Let's Encrypt. Create a `Caddyfile` in your project root:

```caddyfile
# Caddyfile — Replace ipam.example.com with your actual domain.
# Caddy automatically provisions HTTPS certificates from Let's Encrypt.

ipam.example.com {
    reverse_proxy ipam_frontend:80
}
```

**Steps to run:**

1. Add Caddy as a service to your `docker-compose.yml` (or run it standalone):
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

2. Add `caddy_data` to the `volumes:` section at the bottom of your `docker-compose.yml`, then bring everything up:
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
Before deploying to production, ensure you generate cryptographically strong values for your `.env` file:
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
- **Missing permissions**: Ensure `CORS_ORIGINS` in `.env` matches the URL you use to access the frontend.

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
| **Frontend** | React 18 + Vite, Tailwind CSS v4 |
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
