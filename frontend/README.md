# IPAM Frontend

This directory contains the user interface for the IPAM application. It is built using **React 19** and **Vite**, styled with **Tailwind CSS v4**.

## Architecture & Design

- **Framework**: React 19 with Vite 8 as the build tool.
- **Styling**: Tailwind CSS v4 (via the `@tailwindcss/vite` plugin) with a custom dark-mode design system.
- **Routing**: React Router v7 with route guards for authentication.
- **HTTP Client**: Axios with automatic JWT injection and 401 redirect interceptors.
- **Icons**: Lucide React for a consistent icon set.
- **Feature Flags**: The frontend conditionally renders elements (e.g., Discovery Profiles) based on feature flags fetched from `/api/v1/system/features`.

### Design System

The design system is defined in `src/index.css` using Tailwind CSS v4's `@theme` directive. All pages use these shared tokens for visual consistency:

| Token | Purpose | Value |
|-------|---------|-------|
| `--color-bg-primary` | Page background | `#0f1115` |
| `--color-bg-secondary` | Sidebar & cards | `#16191f` |
| `--color-bg-tertiary` | Hover states | `#1f232b` |
| `--color-accent-primary` | Primary accent (indigo) | `#6366f1` |
| `--color-success` | Online/active indicators | `#10b981` |
| `--color-warning` | Warning badges | `#f59e0b` |
| `--color-danger` | Error/conflict states | `#ef4444` |
| `--font-sans` | Typography | Inter (Google Fonts) |

The UI follows a modern dark glassmorphism aesthetic with subtle radial background gradients, glow effects on active elements, and smooth transitions.

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx               # React entry point
│   ├── App.jsx                # Root component: routing, auth guards, setup check
│   ├── index.css              # Tailwind CSS v4 config (@theme tokens, base styles)
│   ├── components/
│   │   └── Layout/
│   │       └── Layout.jsx     # Sidebar navigation, security & discovery warning banners
│   ├── pages/
│   │   ├── Dashboard.jsx      # Aggregate IPAM statistics overview
│   │   ├── Subnets.jsx        # Subnet list, search, create, import/export CSV
│   │   ├── SubnetDetail.jsx   # Single subnet view with IP table, sweep, allocate
│   │   ├── AuditLog.jsx       # Filterable audit trail viewer
│   │   ├── Login.jsx          # Local login form with optional SSO button
│   │   ├── SetupWizard.jsx    # First-run admin creation and SSO config
│   │   ├── SSOSuccess.jsx     # Handles OIDC callback token extraction
│   │   ├── Integrations.jsx   # Multi-vendor integration management UI
│   │   ├── ApprovalQueue.jsx  # Review and approve/dismiss discovered subnets
│   │   └── DiscoveryProfiles.jsx  # SNMPv3 credential profile management
│   ├── lib/
│   │   └── axios.js           # Axios instance with JWT interceptors and env-aware baseURL
│   └── assets/                # Static assets
├── public/                    # Public static files
├── .env.development           # Local dev API URL override (VITE_API_BASE_URL)
├── index.html                 # HTML entry point
├── vite.config.js             # Vite + React + Tailwind plugin config
├── package.json               # Dependencies and scripts
├── nginx.conf                 # Production Nginx config (API proxy + SPA fallback)
├── Dockerfile                 # Multi-stage build (Node build → Nginx serve)
└── eslint.config.js           # ESLint configuration
```

## Pages

| Page | Route | Auth | Description |
|------|-------|------|-------------|
| **Dashboard** | `/` | Required | Shows total subnets, IPs, utilization stats |
| **Subnets** | `/subnets` | Required | List, search, create, import/export subnets |
| **Subnet Detail** | `/subnets/:id` | Required | View IPs, trigger sweeps, allocate/release |
| **Audit Log** | `/audit` | Required | Browse and filter the system audit trail |
| **Integrations** | `/integrations` | Required | Add/edit vendor integrations, test and sync |
| **Approval Queue** | `/approval-queue` | Required | Review subnets discovered by integrations |
| **Discovery Profiles** | `/discovery-profiles` | Required | Manage SNMPv3 credential profiles |
| **Login** | `/login` | None | Username/password login with optional SSO |
| **Setup Wizard** | `/setup` | None | First-run admin account creation |
| **SSO Success** | `/sso-success` | None | Extracts JWT from URL fragment after OIDC flow |

## Prerequisites

- Node.js (Version 22.x or later)
- npm (Node Package Manager)

*Note: If you are using the `start.bat` or `start.ps1` scripts from the root directory, a local version of Node.js is automatically used from the `node_env` folder.*

## Local Development

To run the frontend locally and communicate with a local backend server:

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Development Server**:
   ```bash
   npm run dev
   ```
   This will start the Vite dev server, typically accessible at `http://localhost:5173`. Ensure your backend is also running on `http://localhost:8000`.

   > **Note:** The `.env.development` file sets `VITE_API_BASE_URL=http://localhost:8000/api/v1` so the frontend can reach the backend directly during local dev. In Docker production, this is not needed — the Nginx container proxies `/api/` requests internally, and `axios.js` defaults to the relative path `/api/v1`.

## Building for Production

When deploying via Docker Compose, the `Dockerfile` automatically builds the production bundle and serves it using Nginx.

To manually build the production bundle:
```bash
npm run build
```
This generates the static files in the `dist` directory, which can be hosted on any static file server or CDN.
