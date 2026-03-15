/**
 * Main experiment component that renders the current trial phase
 * and manages transitions between trials and phases.
 */

import { useCallback, useEffect, useRef } from "react";
import type { FC, KeyboardEvent } from "react";
import { useExperiment } from "./useExperiment";
import { useTrial } from "./useTrial";
import { TrialPhase, ExperimentState } from "./types";
import type { StudyConfig, ConditionAssignment, TrialSpec, TrialResult } from "./types";
import Stimulus from "../components/Stimulus";
import Feedback from "../components/Feedback";
import ProgressBar from "../components/ProgressBar";
import { useExperimentStore } from "../store/experimentStore";

interface ExperimentRunnerProps {
  config: StudyConfig;
  condition: ConditionAssignment;
  resumeFrom: number | null;
}

/**
 * Wrapper that renders a single trial. Separated so that each
 * new trial gets a fresh hook instance (keyed by trial index).
 */
const TrialRunner: FC<{
  trialSpec: TrialSpec;
  config: StudyConfig;
  participantId: string;
  sessionId: string;
  onComplete: (result: TrialResult) => void;
}> = ({ trialSpec, config, participantId, sessionId, onComplete }) => {
  const { phase, stimulusAngle, feedbackVisible, feedbackMessage } = useTrial({
    trialSpec,
    timing: config.timing,
    participantId,
    sessionId,
    responseKey: config.response.key,
    onComplete,
  });

  const stimSize = config.ui.stimulus_size_px;

  return (
    <>
      {phase === TrialPhase.ITI && (
        <div>{/* Blank screen during ITI */}</div>
      )}
      {phase === TrialPhase.FIXATION && (
        <div className="fixation">+</div>
      )}
      {phase === TrialPhase.STIMULUS && (
        <Stimulus
          angleDegrees={stimulusAngle}
          sizePx={stimSize}
          bgColor={config.ui.background_color}
        />
      )}
      {phase === TrialPhase.FEEDBACK && (
        <Feedback
          feedbackType={trialSpec.feedback_type}
          message={feedbackMessage}
          visible={feedbackVisible}
        />
      )}
    </>
  );
};

const ExperimentRunner: FC<ExperimentRunnerProps> = ({
  config,
  condition,
  resumeFrom,
}) => {
  const setExperimentState = useExperimentStore((s) => s.setExperimentState);
  const containerRef = useRef<HTMLDivElement>(null);

  const {
    currentTrialIndex,
    currentTrial,
    isPhaseTransition,
    phaseInstructions,
    totalTrials,
    isComplete,
    advanceAfterPhaseScreen,
    completeTrial,
  } = useExperiment(config, condition, resumeFrom);

  // Auto-focus the container so keyboard events are captured
  useEffect(() => {
    containerRef.current?.focus();
  }, [currentTrialIndex, isPhaseTransition]);

  // Navigate to debrief when experiment is done
  useEffect(() => {
    if (isComplete) {
      setExperimentState(ExperimentState.DEBRIEF);
    }
  }, [isComplete, setExperimentState]);

  const handleTrialComplete = useCallback(
    (result: TrialResult) => {
      completeTrial(result);
    },
    [completeTrial],
  );

  const handlePhaseKeyPress = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        advanceAfterPhaseScreen();
      }
    },
    [advanceAfterPhaseScreen],
  );

  // Show progress bar based on config
  const showProgress = config.ui.show_progress;

  return (
    <div
      className="experiment-area no-select"
      ref={containerRef}
      tabIndex={0}
    >
      <ProgressBar
        current={currentTrialIndex}
        total={totalTrials}
        visible={showProgress}
      />

      {isPhaseTransition && (
        <div
          className="phase-instructions"
          onKeyDown={handlePhaseKeyPress}
          tabIndex={0}
          ref={(el) => el?.focus()}
        >
          <h2>Next Phase</h2>
          <p>
            {phaseInstructions ??
              "The next phase of the experiment is about to begin."}
          </p>
          <p style={{ fontSize: "0.95rem", color: "#666" }}>
            Press SPACEBAR or ENTER to continue.
          </p>
        </div>
      )}

      {!isPhaseTransition && currentTrial && (
        <TrialRunner
          key={currentTrial.trial_index_global}
          trialSpec={currentTrial}
          config={config}
          participantId={
            useExperimentStore.getState().participantId ?? ""
          }
          sessionId={useExperimentStore.getState().sessionId ?? ""}
          onComplete={handleTrialComplete}
        />
      )}
    </div>
  );
};

export default ExperimentRunner;
