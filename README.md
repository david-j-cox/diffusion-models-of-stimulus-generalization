# Diffusion Models of Stimulus Generalization

A research-grade web experiment and analytics pipeline for studying history-sensitive stimulus generalization in human operant behavior.

## Overview

Participants are trained on a reinforced target stimulus (S+) along a continuous orientation dimension, then complete generalization probes across nearby and distant stimuli. The system captures trial-by-trial behavioral data for fitting diffusion-style learning models.

**Task**: Go/no-go operant response (spacebar) to oriented line stimuli varying from 20° to 160°.

**Phases**: Practice → Baseline S+ Training → Early Generalization Probes → (Optional Discrimination) → Late Generalization Assessment

## Architecture

```
├── backend/          Python FastAPI + SQLAlchemy + PostgreSQL
├── frontend/         React + Vite + TypeScript (experiment UI)
├── analysis/         Python analysis pipeline + Jupyter notebook
├── outputs/          Generated plots, CSVs, modeling datasets
└── docker-compose.yml
```

## Quick Start (Docker)

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# 2. Start everything
docker compose up --build

# 3. Run database migrations (first time only — also runs automatically on backend start)
docker compose exec backend alembic upgrade head

# 4. Open the experiment
open http://localhost:5173

# 5. API docs
open http://localhost:8000/api/docs
```

## Local Development (without Docker)

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up database
export DATABASE_URL="postgresql+asyncpg://stim_gen:changeme_dev@localhost:5432/stimulus_generalization"
alembic upgrade head

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

### Analysis

```bash
cd analysis
pip install -r requirements.txt

# Generate simulated data first
cd ../backend
python -m scripts.simulate --n-participants 20

# Run the full pipeline
cd ../analysis
python run_pipeline.py --input ../outputs/simulated_trials.csv
```

## Study Configuration

The experiment is driven by YAML configuration files in `backend/app/study_configs/`. The default config (`default_pilot.yaml`) defines:

- **Stimulus**: Orientation (20°–160°), normalized axis [0, 1]
- **Target**: S+ at x = 0.50 (90°)
- **Probes**: 11 positions from 0.10 to 0.90
- **Phases**: Practice (8 trials), Baseline Training (30–60 trials with stability criterion), Early Probes, Late Probes
- **Timing**: 800–1200ms ITI, 500ms fixation, 2000ms stimulus/response window, 1000ms feedback
- **Feedback**: "+1 Point!" on correct S+ responses during training; no feedback on probes

To create a new study design, copy `default_pilot.yaml` and modify. Key areas marked with `# MODIFY HERE` comments.

### Counterbalancing

Add conditions in the YAML to counterbalance target location:

```yaml
conditions:
  - name: "target_left"
    target_x: 0.34
  - name: "target_center"
    target_x: 0.50
  - name: "target_right"
    target_x: 0.66
```

Participants are assigned round-robin with deterministic seeds for reproducibility.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/participants/register` | Register participant, get condition + config |
| POST | `/api/participants/resume` | Resume after disconnect |
| POST | `/api/participants/complete` | Get completion code |
| POST | `/api/participants/screen-event` | Log screen lifecycle event |
| POST | `/api/trials/batch` | Submit batch of trial data (idempotent) |
| GET | `/api/trials/progress/{id}` | Check trial progress |
| GET | `/api/study/config` | Get current study config |
| GET | `/api/study/preview-sequence` | Preview trial sequence |
| GET | `/api/study/preview-stimulus` | Preview stimulus rendering |
| GET | `/api/admin/participants` | List all participants |
| GET | `/api/admin/export/trials.csv` | Export trial data as CSV |
| POST | `/api/admin/exclude` | Flag participant for exclusion |
| POST | `/api/admin/mark-pilot/{id}` | Mark as pilot |
| GET | `/api/health` | Health check |

## Data Export

### Trial-level CSV

```bash
# Via API
curl http://localhost:8000/api/admin/export/trials.csv > trials.csv

# Exclude pilot participants
curl "http://localhost:8000/api/admin/export/trials.csv?exclude_pilots=true" > trials.csv
```

### Analysis Pipeline Outputs

```
outputs/
├── trial_level_clean.csv       # Cleaned trial data
├── participant_summary.csv     # Per-participant summaries
├── gradient_by_block.csv       # Generalization gradients over time
├── modeling_dataset.csv        # Features for model fitting
├── gradient_group.png          # Group mean gradient plot
├── gradient_evolution.png      # Gradient emergence over blocks
├── response_heatmap.png        # Stimulus × block heatmap
├── rt_by_distance.png          # RT as function of distance from S+
└── participant_flow.png        # Exclusion flow diagram
```

## Testing

```bash
# Backend unit tests
cd backend
python -m pytest tests/ -v

# Generate simulated data for analysis testing
python -m scripts.simulate --n-participants 20
```

## Simulating Participants

```bash
cd backend
python -m scripts.simulate --n-participants 30
```

This generates realistic behavioral data with:
- Gaussian generalization gradients (variable width across participants)
- Learning curves during training
- Realistic RT distributions
- A few "poor performer" participants for testing exclusion logic

## Deployment

### Unified Docker (recommended for simple deployments)

```bash
docker compose -f docker-compose.yml up --build -d
```

### Split Deployment (Vercel + Railway/Render/Fly)

**Frontend (Vercel)**:
```bash
cd frontend
npx vercel --prod
# Set env: VITE_API_BASE_URL=https://your-backend-url.com/api
```

**Backend (Railway/Render/Fly)**:
- Set `DATABASE_URL` to your managed PostgreSQL instance
- Set `BACKEND_CORS_ORIGINS` to include your Vercel domain
- Deploy the `backend/` directory with `Dockerfile`
- Run `alembic upgrade head` on first deploy

### Environment Variables

See `.env.example` for all configuration options.

## Extending the Experiment

### Adding a new stimulus dimension
1. Update `stimulus.family` in the YAML config
2. Create a new React component in `frontend/src/components/` (like `Stimulus.tsx` but for your dimension)
3. The normalized axis [0, 1] → rendered value mapping is defined by `axis_min`/`axis_max`

### Adding a new phase
1. Add a phase entry in the YAML `phases` array
2. The sequence generator automatically handles it
3. Set `enabled: false` to skip

### Changing the response format
1. Update `response.mode` in config (`go_nogo` or `two_choice`)
2. Modify `useTrial.ts` to handle the new response format

### Fitting a diffusion model
1. Run the analysis pipeline to generate `modeling_dataset.csv`
2. See `analysis/starter_model.py` for a baseline logistic approach
3. The dataset includes cumulative similarity-weighted reinforcement history and other features needed for a mechanistic diffusion process model

## License

Research use. See LICENSE file.
