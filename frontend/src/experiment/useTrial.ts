/**
 * Hook for running a single trial through its state machine:
 * ITI -> FIXATION -> STIMULUS -> FEEDBACK -> DONE
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { TrialPhase, type TrialSpec, type TrialResult, type TimingConfig } from "./types";
import { isoNow } from "../utils/timing";

export interface UseTrialOptions {
  trialSpec: TrialSpec;
  timing: TimingConfig;
  participantId: string;
  sessionId: string;
  responseKey: string;
  onComplete: (result: TrialResult) => void;
}

export interface UseTrialReturn {
  phase: TrialPhase;
  stimulusAngle: number;
  feedbackVisible: boolean;
  feedbackMessage: string;
  itiDuration: number;
}

export function useTrial({
  trialSpec,
  timing,
  participantId,
  sessionId,
  responseKey,
  onComplete,
}: UseTrialOptions): UseTrialReturn {
  const [phase, setPhase] = useState<TrialPhase>(TrialPhase.ITI);
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState("");

  // Stable refs for mutable state that doesn't trigger re-renders
  const responseOccurredRef = useRef(false);
  const responseCountRef = useRef(0);
  const firstResponseRtRef = useRef<number | null>(null);
  const allTimestampsRef = useRef<number[]>([]);
  const stimulusOnsetRef = useRef(0);
  const stimulusOnsetIsoRef = useRef("");
  const trialStartIsoRef = useRef("");
  const itiDurationRef = useRef(0);
  const phaseRef = useRef<TrialPhase>(TrialPhase.ITI);
  const completedRef = useRef(false);
  const rafIdRef = useRef(0);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  // Keep a stable ref for trialSpec to avoid closure issues
  const trialSpecRef = useRef(trialSpec);
  trialSpecRef.current = trialSpec;

  // Compute random ITI duration
  const itiDuration = useRef(
    timing.iti_min_ms +
      Math.random() * (timing.iti_max_ms - timing.iti_min_ms),
  ).current;

  // Build and emit the TrialResult
  const emitResult = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;

    const spec = trialSpecRef.current;
    const reinforcementDelivered =
      spec.reinforcement_available && responseOccurredRef.current;

    const result: TrialResult = {
      participant_id: participantId,
      session_id: sessionId,
      trial_index_global: spec.trial_index_global,
      trial_index_within_phase: spec.trial_index_within_phase,
      block_index: spec.block_index,
      phase_id: spec.phase_id,
      stimulus_x_normalized: spec.stimulus_x_normalized,
      stimulus_render_value: spec.stimulus_render_value,
      stimulus_label: spec.stimulus_label,
      trial_type: spec.trial_type,
      reinforcement_available: spec.reinforcement_available,
      reinforcement_delivered: reinforcementDelivered,
      feedback_type: spec.feedback_type,
      is_attention_check: spec.is_attention_check,
      response_occurred: responseOccurredRef.current,
      response_count: responseCountRef.current,
      first_response_rt_ms: firstResponseRtRef.current,
      all_response_timestamps_ms: [...allTimestampsRef.current],
      iti_duration_ms: itiDurationRef.current,
      stimulus_onset_ts: stimulusOnsetIsoRef.current,
      trial_start_ts: trialStartIsoRef.current,
      trial_end_ts: isoNow(),
      // These will be filled in by useExperiment.completeTrial
      similarity_to_target_gaussian: 0,
      similarity_to_target_exponential: 0,
    };

    onCompleteRef.current(result);
  }, [participantId, sessionId]);

  // Phase timing via requestAnimationFrame
  useEffect(() => {
    trialStartIsoRef.current = isoNow();
    itiDurationRef.current = itiDuration;
    completedRef.current = false;
    responseOccurredRef.current = false;
    responseCountRef.current = 0;
    firstResponseRtRef.current = null;
    allTimestampsRef.current = [];

    let startTime = performance.now();
    phaseRef.current = TrialPhase.ITI;
    setPhase(TrialPhase.ITI);

    function tick() {
      const elapsed = performance.now() - startTime;
      const currentPhase = phaseRef.current;

      if (currentPhase === TrialPhase.ITI) {
        if (elapsed >= itiDuration) {
          phaseRef.current = TrialPhase.FIXATION;
          setPhase(TrialPhase.FIXATION);
          startTime = performance.now();
        }
      } else if (currentPhase === TrialPhase.FIXATION) {
        if (elapsed >= timing.fixation_ms) {
          phaseRef.current = TrialPhase.STIMULUS;
          setPhase(TrialPhase.STIMULUS);
          stimulusOnsetRef.current = performance.now();
          stimulusOnsetIsoRef.current = isoNow();
          startTime = performance.now();
        }
      } else if (currentPhase === TrialPhase.STIMULUS) {
        if (elapsed >= timing.stimulus_ms) {
          // Stimulus time ended — check if feedback is needed
          const spec = trialSpecRef.current;
          const shouldShowFeedback =
            spec.reinforcement_available &&
            responseOccurredRef.current &&
            spec.feedback_type === "points";

          if (shouldShowFeedback) {
            phaseRef.current = TrialPhase.FEEDBACK;
            setPhase(TrialPhase.FEEDBACK);
            setFeedbackVisible(true);
            setFeedbackMessage("+1 Point!");
            startTime = performance.now();
          } else {
            phaseRef.current = TrialPhase.DONE;
            setPhase(TrialPhase.DONE);
            emitResult();
            return; // Stop loop
          }
        }
      } else if (currentPhase === TrialPhase.FEEDBACK) {
        if (elapsed >= timing.feedback_ms) {
          setFeedbackVisible(false);
          phaseRef.current = TrialPhase.DONE;
          setPhase(TrialPhase.DONE);
          emitResult();
          return; // Stop loop
        }
      } else {
        // DONE — stop
        return;
      }

      rafIdRef.current = requestAnimationFrame(tick);
    }

    rafIdRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafIdRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trialSpec.trial_index_global]);

  // Keyboard listener
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== responseKey) return;
      if (phaseRef.current !== TrialPhase.STIMULUS) return;

      e.preventDefault();
      const now = performance.now();
      const rtFromOnset = now - stimulusOnsetRef.current;

      responseCountRef.current++;
      allTimestampsRef.current.push(Math.round(rtFromOnset * 100) / 100);

      if (!responseOccurredRef.current) {
        responseOccurredRef.current = true;
        firstResponseRtRef.current = Math.round(rtFromOnset * 100) / 100;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [responseKey, trialSpec.trial_index_global]);

  return {
    phase,
    stimulusAngle: trialSpec.stimulus_render_value,
    feedbackVisible,
    feedbackMessage,
    itiDuration,
  };
}
