# IPAM Frontend

This directory contains the user interface for the IPAM application. It is built using **React** and **Vite** and uses vanilla CSS for styling.

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

## Building for Production

When deploying via Docker Compose, the `Dockerfile` automatically builds the production bundle and serves it using Nginx.

To manually build the production bundle:
```bash
npm run build
```
This generates the static files in the `dist` directory, which can be hosted on any static file server or CDN.
