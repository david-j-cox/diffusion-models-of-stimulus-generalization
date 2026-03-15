# TODO

## Pre-Pilot (must do before first real participant)

- [ ] Run `docker compose up --build` end-to-end and verify full participant flow from consent to completion code
- [ ] Verify trial data lands correctly in PostgreSQL — run a simulated session and inspect the `trials` table
- [ ] Run `npm install` and confirm frontend builds cleanly with no TypeScript errors
- [ ] Test resume flow: refresh mid-experiment and confirm data is not lost and trial index picks up correctly
- [ ] Review consent screen text with IRB language for your institution
- [ ] Review instructions screen text for clarity and accuracy
- [ ] Set a real `SECRET_KEY` and `POSTGRES_PASSWORD` in `.env` before any deployment
- [ ] Run the simulator (`python -m scripts.simulate`) and pipe output through the full analysis pipeline to confirm it works end-to-end
- [ ] Confirm the Jupyter notebook runs cleanly on simulated data

## Experiment Design Validation

- [ ] Pilot with 3–5 participants to check timing feels right (ITI, stimulus duration, feedback)
- [ ] Verify stimulus rendering across browsers (Chrome, Firefox, Safari) — SVG orientation line
- [ ] Check that the stability criterion for baseline training terminates at a reasonable trial count
- [ ] Decide on final probe repetitions per phase (currently 2 early, 4 late) — may need more for stable gradient estimation
- [ ] Decide whether to enable the discrimination phase and configure S- positions
- [ ] Determine final exclusion thresholds (min RT, max missed fraction, practice failure)

## Frontend

- [ ] Add `beforeunload` warning if experiment is in progress (prevent accidental tab close)
- [ ] Add focus-loss detection and logging (document.visibilitychange)
- [ ] Test on smaller laptop screens (1366×768) — verify stimulus is visible and centered
- [ ] Add optional fullscreen prompt at experiment start
- [ ] Add a "break" screen between phases if experiment exceeds ~10 minutes
- [ ] Confirm Prolific/MTurk/SONA URL parameter parsing works for your recruitment platform

## Backend

- [ ] Add rate limiting on registration endpoint to prevent abuse
- [ ] Add authentication to admin endpoints (currently open)
- [ ] Add a `/api/admin/export/screen_events.csv` endpoint for screen-level event export
- [ ] Add automated exclusion checks that run on completion (fast RT, missed trials)
- [ ] Test idempotent trial batch submission under simulated network failure (double-submit)
- [ ] Add database backup strategy for production deployment

## Analysis Pipeline

- [ ] Validate gradient computation against a known analytic case (e.g., perfect Gaussian responder)
- [ ] Add between-condition comparison plots (if using multiple conditions)
- [ ] Add individual differences analysis (gradient width correlations, cluster analysis)
- [ ] Extend starter model to a proper mechanistic diffusion process (e.g., PyDDM or custom Stan model)
- [ ] Add power analysis script to estimate required N for detecting gradient differences

## Deployment

- [ ] Choose deployment target (Docker on a VM, or Vercel + Railway split)
- [ ] Set up production PostgreSQL with SSL
- [ ] Configure CORS for production domain
- [ ] Set up HTTPS
- [ ] Add monitoring/alerting for backend uptime during data collection
- [ ] Push `main` branch to remote when ready to mark v1.0

## Nice-to-Have (post-pilot)

- [ ] Add a lightweight admin dashboard (participant list, completion rates, live gradient preview)
- [ ] Add configurable audio feedback option
- [ ] Support additional stimulus families (color hue, spatial frequency, gabor patches)
- [ ] Add adaptive probe placement based on early gradient shape
- [ ] Add a two-choice classification response mode variant
- [ ] Add multi-session support (participants return on different days)
