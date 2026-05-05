# IPAM: Zero-Touch Enterprise IP Address Management

IPAM is a modern, responsive, and automated IP Address Management system designed to be "zero-touch" out of the box while providing the flexibility required for enterprise environments.

## Features
- **Zero-Touch Setup**: An embedded Setup Wizard handles database migrations, initial admin creation, and configuration via the UI.
- **Automated Discovery**: Optional background workers (Celery) can automatically scan your subnets using ICMP/SNMP to find active hosts and flag conflicts.
- **Role-Based Access Control**: Strict separation between `admin` and `readonly` users, with full OIDC Single Sign-On (SSO) support.
- **IPv6 Ready**: Full support for IPv4 and IPv6 address management with protocol-agnostic networking logic.

---

## Quick Start (Docker)

The fastest way to run IPAM is using Docker Compose. This starts the core application (Frontend, Backend, Database, and Redis).

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/IPAM.git
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
For production use, you **MUST** place IPAM behind a Reverse Proxy to handle SSL/TLS termination. Recommended proxies include:
- Traefik
- Nginx Proxy Manager
- Cloudflare Tunnels
- Caddy

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

## Local Development Setup

If you wish to contribute or modify the code locally without Docker, please see the specific README files in the respective directories:
- **[Backend Setup & API](backend/README.md)**
- **[Frontend Setup & UI](frontend/README.md)**

Alternatively, you can run the provided helper scripts (`start.bat` on Windows or `start.ps1` for PowerShell) to quickly spin up the local development servers.
