# Argus — Project Setup

## Prerequisites

Docker must already be installed. All other tools are installed below.

## 1. Install Make

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install -y make
```

### Linux (Fedora/RHEL)
```bash
sudo dnf install -y make
```

### Windows
Install [Chocolatey](https://chocolatey.org/install), then:
```powershell
choco install make
```

Or install [GnuWin32 Make](https://gnuwin32.sourceforge.net/packages/make.htm) and add it to your PATH.

## 2. Install uv (Python package manager)

### Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installation. Verify:
```bash
uv --version
```

## 3. Install pnpm (Node.js package manager)

Install:

```bash
npm install -g pnpm@latest-10
```

Verify:
```bash
pnpm --version
```


## 4. Spin up infrastructure

From the project root:
```bash
docker compose up -d
```


## 5. Install dependencies and configure pre-commit hook

```bash
make install
```


## 6. Configure environment variables

Copy the example env file and fill in your values:
```bash
cp .env.example .env
```


## 8. Start the services

In separate terminals:
```bash
make run-gateway    # FastAPI on http://localhost:8000
make run-agents     # Celery worker
```

## 9. Start the web dashboard (optional)

```bash
cd apps/web
pnpm install
pnpm dev            # Next.js on http://localhost:3000
```