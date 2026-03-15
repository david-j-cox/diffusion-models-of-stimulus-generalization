/* ── Experiment state machine ─────────────────────────────────────────────── */

export enum ExperimentState {
  CONSENT = "CONSENT",
  ELIGIBILITY = "ELIGIBILITY",
  INSTRUCTIONS = "INSTRUCTIONS",
  PRACTICE = "PRACTICE",
  RUNNING = "RUNNING",
  DEBRIEF = "DEBRIEF",
  COMPLETE = "COMPLETE",
}

/* ── Trial-level state machine ───────────────────────────────────────────── */

export enum TrialPhase {
  ITI = "ITI",
  FIXATION = "FIXATION",
  STIMULUS = "STIMULUS",
  FEEDBACK = "FEEDBACK",
  DONE = "DONE",
}

/* ── Study configuration (mirrors YAML) ──────────────────────────────────── */

export interface StimulusConfig {
  family: string;
  dimension_label: string;
  axis_min: number;
  axis_max: number;
  axis_unit: string;
  target_x: number;
  probe_positions: number[];
  s_minus_positions: number[] | null;
  similarity: {
    gaussian_sigma: number;
    exponential_tau: number;
  };
}

export interface TimingConfig {
  iti_min_ms: number;
  iti_max_ms: number;
  fixation_ms: number;
  stimulus_ms: number;
  response_window_ms: number;
  feedback_ms: number;
}

export interface FeedbackConfig {
  positive_message: string;
  negative_message: string;
  neutral_message: string;
  show_points: boolean;
}

export interface ResponseConfig {
  key: string;
  key_label: string;
  mode: string;
}

export interface RandomizationConfig {
  max_run_same_type: number;
  max_run_same_stimulus: number;
}

export interface StabilityConfig {
  min_trials: number;
  window_size: number;
  threshold: number;
}

export interface PhaseConfig {
  id: string;
  type: string;
  enabled: boolean;
  block_index: number;
  target_count?: number;
  reinforcement_available?: boolean;
  feedback_type?: string;
  instructions?: string;
  use_stability_criterion?: boolean;
  max_trials?: number;
  attention_check_count?: number;
  probe_repetitions?: number;
  target_in_probe_count?: number;
  probe_reinforcement?: boolean;
  s_minus_count?: number;
  s_minus_feedback_type?: string;
  stimuli?: StimulusSpec[];
}

export interface StimulusSpec {
  x: number;
  count: number;
  trial_type: string;
  reinforcement_available: boolean;
  feedback_type: string | null;
  is_attention_check?: boolean;
}

export interface QualityControlConfig {
  min_rt_ms: number;
  max_missed_fraction: number;
  max_focus_losses: number;
  check_duplicate_ids: boolean;
  practice_failure_threshold: number;
}

export interface UIConfig {
  show_progress: boolean;
  require_fullscreen: boolean;
  warn_mobile: boolean;
  background_color: string;
  stimulus_size_px: number;
}

export interface StudyConfig {
  name: string;
  version: string;
  stimulus: StimulusConfig;
  conditions: Array<{ name: string; target_x: number }>;
  timing: TimingConfig;
  feedback: FeedbackConfig;
  response: ResponseConfig;
  randomization: RandomizationConfig;
  stability: StabilityConfig;
  phases: PhaseConfig[];
  quality_control: QualityControlConfig;
  ui: UIConfig;
}

/* ── Condition assignment from registration ──────────────────────────────── */

export interface ConditionAssignment {
  condition_name: string;
  condition_index: number;
  target_x: number;
  random_seed: number;
  assignment: string;
}

/* ── Trial specification (generated client-side) ─────────────────────────── */

export interface TrialSpec {
  phase_id: string;
  block_index: number;
  trial_index_global: number;
  trial_index_within_phase: number;
  stimulus_x_normalized: number;
  stimulus_render_value: number;
  stimulus_label: string;
  trial_type: string;
  reinforcement_available: boolean;
  feedback_type: string | null;
  is_attention_check: boolean;
}

/* ── Trial result (logged to API) ────────────────────────────────────────── */

export interface TrialResult {
  participant_id: string;
  session_id: string;
  trial_index_global: number;
  trial_index_within_phase: number;
  block_index: number;
  phase_id: string;
  stimulus_x_normalized: number;
  stimulus_render_value: number;
  stimulus_label: string;
  trial_type: string;
  reinforcement_available: boolean;
  reinforcement_delivered: boolean;
  feedback_type: string | null;
  is_attention_check: boolean;
  response_occurred: boolean;
  response_count: number;
  first_response_rt_ms: number | null;
  all_response_timestamps_ms: number[];
  iti_duration_ms: number;
  stimulus_onset_ts: string;
  trial_start_ts: string;
  trial_end_ts: string;
  similarity_to_target_gaussian: number;
  similarity_to_target_exponential: number;
}
