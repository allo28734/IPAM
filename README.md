# IPAM
IP Address Management Software

A Zero-Touch Enterprise IP Address Management application.

## Deployment

Deploying IPAM is designed to be simple and "zero-touch" out of the box, with full flexibility for enterprise environments.

### Standard Setup (Lightweight)
Run the following command to start the core application (Frontend, Backend, and embedded Database/Redis). This setup does not include background network scanning (saving RAM).

```bash
docker compose up -d
```
Visit `http://<your-server-ip>` and follow the Setup Wizard in your browser.

### Enable Network Discovery (Background Scanning)
If you want to use the automated background network scanning (Celery workers), you must include the `discovery` profile when starting the application:

```bash
docker compose --profile discovery up -d
```
You can then enable Network Discovery from the Setup Wizard or Settings.

### Production Security: Reverse Proxy (HTTPS)
**IMPORTANT**: The built-in Nginx container serves the application over **Plain HTTP on port 80**. It does not enforce HTTPS. 
For production use, you **MUST** place IPAM behind a Reverse Proxy (such as Traefik, Nginx Proxy Manager, Cloudflare Tunnels, or Caddy) to handle SSL/TLS termination and secure the traffic.

### Bring Your Own Database (BYOD)
By default, the application embeds its own secure PostgreSQL and Redis containers. If you already have dedicated infrastructure, you can override these defaults.

1. Create a `.env` file in the same directory as `docker-compose.yml`.
2. Define the external connection strings:
   ```env
   EXTERNAL_DB_URL=postgresql://user:password@your-db-cluster:5432/ipam
   EXTERNAL_REDIS_URL=redis://:password@your-redis-cluster:6379/0
   ```
3. Comment out the `db` and `redis` service blocks in `docker-compose.yml`.
4. Run `docker compose up -d`.
