# smathhacks2026

Local stack for:
- HoloOcean viewport API (`holoocean/api.py`)
- FastAPI backend (`backend/main.py`)
- React frontend (`client/`)
- Demo telemetry client (`scripts/demo_client.py`)

## Prerequisites
- Docker + Docker Compose
- Python 3.13+
- `uv` (`https://docs.astral.sh/uv/`)
- Node.js + npm
- HoloOcean installed and working locally

## One-Time Setup
1. Install Python dependencies:
```bash
uv sync
```
2. Install frontend dependencies:
```bash
cd client
npm install
cd ..
```
3. Load command aliases:
```bash
source /home/chris/code/ncssm/smathhacks26/command_aliases.sh
```

Optional persistent load:
```bash
echo "source /home/chris/code/ncssm/smathhacks26/command_aliases.sh" >> ~/.bashrc
source ~/.bashrc
```

## Alias Reference
- `run_holoocean_api`
Starts HoloOcean API on `http://localhost:8900`.

- `run_backend`
Runs `docker compose up -d` first (Postgres), then starts backend on `http://localhost:8000` using `backend/.env`.

- `run_frontend`
Starts Vite dev server for the frontend (typically `http://localhost:5173`).

- `run_client`
Starts the demo client loop that sends random images from `train/` to backend.

- `run_all`
Starts Docker Compose and then launches HoloOcean API + backend + frontend + demo client together.  
Press `Ctrl+C` to stop; child processes are cleaned up automatically.

- `ask_holo {-1|0|1}`
Fetches the latest JPG frame from HoloOcean API for the requested `agent_index`, saves it to `/tmp`, and opens it.

## ask_holo Examples
```bash
ask_holo -1   # any active viewport (auto)
ask_holo 0    # agent index 0
ask_holo 1    # agent index 1
```

## Dynamic Viewport Offsets (No Restart)
You can change camera translation and angular offsets while `holoocean/api.py` is running.

Get current offsets:
```bash
curl -sS http://localhost:8900/viewport/offset
```

Set translation offset only (`x,y,z`):
```bash
curl -sS -X POST http://localhost:8900/viewport/offset \
  -H "Content-Type: application/json" \
  -d '{"position_offset":[0,0,6]}'
```

Set angular offset only (`roll,pitch,yaw` in degrees):
```bash
curl -sS -X POST http://localhost:8900/viewport/offset \
  -H "Content-Type: application/json" \
  -d '{"angles_offset_deg":[0,-15,30]}'
```

Set both at once:
```bash
curl -sS -X POST http://localhost:8900/viewport/offset \
  -H "Content-Type: application/json" \
  -d '{"position_offset":[0,0,6],"angles_offset_deg":[0,-15,30]}'
```

Then immediately request a frame:
```bash
ask_holo 0
```

If your HoloOcean API is not on localhost:8900:
```bash
export HOLO_API_BASE="http://<host>:<port>"
ask_holo 0
```

## Normal Workflow
1. Source aliases:
```bash
source /home/chris/code/ncssm/smathhacks26/command_aliases.sh
```
2. Start everything:
```bash
run_all
```
3. In another shell, test camera capture:
```bash
ask_holo -1
```

## Troubleshooting
- `run_backend` fails with DB errors:
Ensure Docker is running, then check:
```bash
docker compose ps
```
- `ask_holo` returns HTTP 503:
HoloOcean has not produced a frame yet; wait a few seconds and retry.
- `ask_holo` saves image but does not open:
Install an opener (`xdg-open` on Linux or `open` on macOS), or open the saved file manually from `/tmp`.
