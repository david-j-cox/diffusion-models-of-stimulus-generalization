/**
 * Hook that manages the full experiment lifecycle: sequence generation,
 * trial progression, buffering, and flushing results to the API.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ConditionAssignment,
  StudyConfig,
  TrialSpec,
  TrialResult,
  PhaseConfig,
  StimulusSpec,
} from "./types";
import { submitTrialBatch, flushTrialBatchBeacon } from "../api/client";
import { useExperimentStore } from "../store/experimentStore";

/* ── Seeded PRNG (Mulberry32) ────────────────────────────────────────────── */

function mulberry32(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ── Sequence generation (port of Python logic) ──────────────────────────── */

function renderValue(xNorm: number, axisMin: number, axisMax: number): number {
  return axisMin + xNorm * (axisMax - axisMin);
}

function labelForStimulus(
  xNorm: number,
  targetX: number,
  sMinus: number[] | null,
  tolerance = 1e-6,
): string {
  if (Math.abs(xNorm - targetX) < tolerance) return "S+";
  if (sMinus) {
    for (const sm of sMinus) {
      if (Math.abs(xNorm - sm) < tolerance) return "S-";
    }
  }
  return "probe";
}

function expandPhaseStimuli(
  phaseCfg: PhaseConfig,
  targetX: number,
  probePositions: number[],
  sMinus: number[] | null,
): PhaseConfig {
  if (phaseCfg.stimuli && phaseCfg.stimuli.length > 0) return phaseCfg;

  const stimuli: StimulusSpec[] = [];

  // Training trials at S+
  const targetCount = phaseCfg.target_count ?? 0;
  if (targetCount > 0) {
    stimuli.push({
      x: targetX,
      count: targetCount,
      trial_type: "training",
      reinforcement_available: phaseCfg.reinforcement_available ?? true,
      feedback_type: phaseCfg.feedback_type ?? "points",
    });
  }

  // Probe trials
  const probeReps = phaseCfg.probe_repetitions ?? 0;
  if (probeReps > 0) {
    for (const px of probePositions) {
      stimuli.push({
        x: px,
        count: probeReps,
        trial_type: "probe",
        reinforcement_available: phaseCfg.probe_reinforcement ?? false,
        feedback_type: null,
      });
    }
    const targetInProbe = phaseCfg.target_in_probe_count ?? 0;
    if (targetInProbe > 0) {
      stimuli.push({
        x: targetX,
        count: targetInProbe,
        trial_type: "training",
        reinforcement_available: true,
        feedback_type: phaseCfg.feedback_type ?? "points",
      });
    }
  }

  // Discrimination S- trials
  if (sMinus && phaseCfg.type === "discrimination") {
    const sMinusCount = phaseCfg.s_minus_count ?? 0;
    for (const sm of sMinus) {
      stimuli.push({
        x: sm,
        count: sMinusCount,
        trial_type: "discrimination",
        reinforcement_available: false,
        feedback_type: phaseCfg.s_minus_feedback_type ?? "none",
      });
    }
  }

  // Attention checks
  const attnCount = phaseCfg.attention_check_count ?? 0;
  if (attnCount > 0) {
    stimuli.push({
      x: targetX,
      count: attnCount,
      trial_type: "training",
      reinforcement_available: true,
      feedback_type: "points",
      is_attention_check: true,
    });
  }

  return { ...phaseCfg, stimuli };
}

function countViolations(
  trials: TrialSpec[],
  maxRunType: number,
  maxRunStim: number,
): number {
  let violations = 0;
  for (let i = 0; i < trials.length; i++) {
    if (i >= maxRunType) {
      let allSameType = true;
      for (let j = 0; j < maxRunType; j++) {
        if (trials[i - j].trial_type !== trials[i].trial_type) {
          allSameType = false;
          break;
        }
      }
      if (allSameType) violations++;
    }
    if (i >= maxRunStim) {
      let allSameStim = true;
      for (let j = 0; j < maxRunStim; j++) {
        if (
          Math.abs(
            trials[i - j].stimulus_x_normalized -
              trials[i].stimulus_x_normalized,
          ) >= 1e-6
        ) {
          allSameStim = false;
          break;
        }
      }
      if (allSameStim) violations++;
    }
  }
  return violations;
}

function constrainedShuffle(
  trials: TrialSpec[],
  rand: () => number,
  maxRunType: number,
  maxRunStim: number,
  maxAttempts = 500,
): TrialSpec[] {
  let best = [...trials];
  let bestV = countViolations(best, maxRunType, maxRunStim);

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const candidate = [...trials];
    // Fisher-Yates shuffle with seeded RNG
    for (let i = candidate.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [candidate[i], candidate[j]] = [candidate[j], candidate[i]];
    }
    const v = countViolations(candidate, maxRunType, maxRunStim);
    if (v === 0) return candidate;
    if (v < bestV) {
      best = candidate;
      bestV = v;
    }
  }
  return best;
}

function generatePhaseTrials(
  phaseCfg: PhaseConfig,
  targetX: number,
  sMinus: number[] | null,
  axisMin: number,
  axisMax: number,
  rand: () => number,
  maxRunType: number,
  maxRunStim: number,
): TrialSpec[] {
  const phaseId = phaseCfg.id;
  const pool: TrialSpec[] = [];

  for (const stimSpec of phaseCfg.stimuli ?? []) {
    const label = labelForStimulus(stimSpec.x, targetX, sMinus);
    for (let c = 0; c < stimSpec.count; c++) {
      pool.push({
        phase_id: phaseId,
        block_index: phaseCfg.block_index,
        trial_index_global: 0, // assigned later
        trial_index_within_phase: 0,
        stimulus_x_normalized: stimSpec.x,
        stimulus_render_value: renderValue(stimSpec.x, axisMin, axisMax),
        stimulus_label: label,
        trial_type: stimSpec.trial_type,
        reinforcement_available: stimSpec.reinforcement_available,
        feedback_type: stimSpec.feedback_type,
        is_attention_check: stimSpec.is_attention_check ?? false,
      });
    }
  }

  return constrainedShuffle(pool, rand, maxRunType, maxRunStim);
}

function generateFullSequence(
  config: StudyConfig,
  targetX: number,
  seed: number,
): TrialSpec[] {
  const rand = mulberry32(seed);
  const { axis_min: axisMin, axis_max: axisMax } = config.stimulus;
  const probePositions = config.stimulus.probe_positions;
  const sMinus = config.stimulus.s_minus_positions;
  const maxRunType = config.randomization.max_run_same_type;
  const maxRunStim = config.randomization.max_run_same_stimulus;

  const allTrials: TrialSpec[] = [];
  let globalIdx = 0;

  for (const phaseCfg of config.phases) {
    if (!phaseCfg.enabled) continue;
    const expanded = expandPhaseStimuli(phaseCfg, targetX, probePositions, sMinus);
    const phaseTrials = generatePhaseTrials(
      expanded,
      targetX,
      sMinus,
      axisMin,
      axisMax,
      rand,
      maxRunType,
      maxRunStim,
    );
    for (let localIdx = 0; localIdx < phaseTrials.length; localIdx++) {
      phaseTrials[localIdx].trial_index_global = globalIdx;
      phaseTrials[localIdx].trial_index_within_phase = localIdx;
      phaseTrials[localIdx].block_index = phaseCfg.block_index;
      globalIdx++;
    }
    allTrials.push(...phaseTrials);
  }

  return allTrials;
}

/* ── Similarity kernels ──────────────────────────────────────────────────── */

function gaussianSimilarity(
  x: number,
  target: number,
  sigma: number,
): number {
  const d = x - target;
  return Math.exp(-(d * d) / (2 * sigma * sigma));
}

function exponentialSimilarity(
  x: number,
  target: number,
  tau: number,
): number {
  return Math.exp(-Math.abs(x - target) / tau);
}

/* ── Hook ─────────────────────────────────────────────────────────────────── */

const BATCH_SIZE = 5;

export interface UseExperimentReturn {
  trials: TrialSpec[];
  currentTrialIndex: number;
  currentTrial: TrialSpec | null;
  currentPhaseId: string | null;
  isPhaseTransition: boolean;
  phaseInstructions: string | null;
  totalTrials: number;
  isComplete: boolean;
  advanceAfterPhaseScreen: () => void;
  completeTrial: (result: TrialResult) => void;
}

export function useExperiment(
  config: StudyConfig | null,
  condition: ConditionAssignment | null,
  resumeFrom: number | null,
): UseExperimentReturn {
  const participantId = useExperimentStore((s) => s.participantId);
  const sessionId = useExperimentStore((s) => s.sessionId);
  const addPoints = useExperimentStore((s) => s.addPoints);

  // Generate the full trial sequence once
  const trials = useMemo(() => {
    if (!config || !condition) return [];
    return generateFullSequence(config, condition.target_x, condition.random_seed);
  }, [config, condition]);

  const [currentTrialIndex, setCurrentTrialIndex] = useState(resumeFrom ?? 0);
  const [isPhaseTransition, setIsPhaseTransition] = useState(false);
  const [phaseInstructions, setPhaseInstructions] = useState<string | null>(null);
  const bufferRef = useRef<TrialResult[]>([]);
  const lastPhaseIdRef = useRef<string | null>(null);

  // Determine current trial
  const currentTrial = currentTrialIndex < trials.length ? trials[currentTrialIndex] : null;
  const currentPhaseId = currentTrial?.phase_id ?? null;
  const isComplete = currentTrialIndex >= trials.length && trials.length > 0;

  // Flush buffer to API
  const flush = useCallback(async () => {
    if (bufferRef.current.length === 0) return;
    if (!participantId || !sessionId) return;
    const toSend = [...bufferRef.current];
    bufferRef.current = [];
    try {
      await submitTrialBatch({
        participant_id: participantId,
        session_id: sessionId,
        trials: toSend,
      });
    } catch {
      // Re-add to buffer on failure so they're not lost
      bufferRef.current = [...toSend, ...bufferRef.current];
    }
  }, [participantId, sessionId]);

  // Beacon flush on beforeunload
  useEffect(() => {
    const handler = () => {
      if (bufferRef.current.length > 0 && participantId && sessionId) {
        flushTrialBatchBeacon({
          participant_id: participantId,
          session_id: sessionId,
          trials: bufferRef.current,
        });
        bufferRef.current = [];
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [participantId, sessionId]);

  // Detect phase transitions
  useEffect(() => {
    if (!currentTrial) return;
    if (lastPhaseIdRef.current !== null && lastPhaseIdRef.current !== currentTrial.phase_id) {
      // Phase changed — show transition screen
      const phaseCfg = config?.phases.find((p) => p.id === currentTrial.phase_id);
      setPhaseInstructions(phaseCfg?.instructions ?? null);
      setIsPhaseTransition(true);
    }
    lastPhaseIdRef.current = currentTrial.phase_id;
  }, [currentTrial, config]);

  // Show initial phase instructions on first trial
  useEffect(() => {
    if (trials.length > 0 && lastPhaseIdRef.current === null) {
      const firstPhase = config?.phases.find((p) => p.id === trials[0].phase_id);
      if (firstPhase?.instructions) {
        setPhaseInstructions(firstPhase.instructions);
        setIsPhaseTransition(true);
      }
      lastPhaseIdRef.current = trials[0].phase_id;
    }
  }, [trials, config]);

  const advanceAfterPhaseScreen = useCallback(() => {
    setIsPhaseTransition(false);
    setPhaseInstructions(null);
  }, []);

  const completeTrial = useCallback(
    (result: TrialResult) => {
      if (!config || !condition) return;

      // Compute similarity values
      const sigma = config.stimulus.similarity.gaussian_sigma;
      const tau = config.stimulus.similarity.exponential_tau;
      result.similarity_to_target_gaussian = gaussianSimilarity(
        result.stimulus_x_normalized,
        condition.target_x,
        sigma,
      );
      result.similarity_to_target_exponential = exponentialSimilarity(
        result.stimulus_x_normalized,
        condition.target_x,
        tau,
      );

      // Points
      if (result.reinforcement_delivered && config.feedback.show_points) {
        addPoints(1);
      }

      bufferRef.current.push(result);

      const nextIndex = currentTrialIndex + 1;

      // Flush on batch size or phase boundary
      const nextTrial = nextIndex < trials.length ? trials[nextIndex] : null;
      const phaseBoundary = nextTrial?.phase_id !== currentTrial?.phase_id;
      if (
        bufferRef.current.length >= BATCH_SIZE ||
        phaseBoundary ||
        nextIndex >= trials.length
      ) {
        flush();
      }

      setCurrentTrialIndex(nextIndex);
    },
    [config, condition, currentTrialIndex, trials, currentTrial, addPoints, flush],
  );

  return {
    trials,
    currentTrialIndex,
    currentTrial,
    currentPhaseId,
    isPhaseTransition,
    phaseInstructions,
    totalTrials: trials.length,
    isComplete,
    advanceAfterPhaseScreen,
    completeTrial,
  };
}
