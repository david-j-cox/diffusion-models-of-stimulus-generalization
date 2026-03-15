/**
 * Main application component. Manages the experiment flow through screens:
 * consent -> eligibility -> instructions -> experiment -> debrief -> completion
 */

import { useCallback, useEffect, useState } from "react";
import type { FC } from "react";
import { ExperimentState } from "./experiment/types";
import { useExperimentStore } from "./store/experimentStore";
import { registerParticipant, logScreenEvent, completeExperiment } from "./api/client";
import { getUserAgent, getViewportSize, getTimezoneOffset } from "./utils/browser";
import { isoNow } from "./utils/timing";

import ConsentScreen from "./components/ConsentScreen";
import EligibilityScreen from "./components/EligibilityScreen";
import InstructionsScreen from "./components/InstructionsScreen";
import ExperimentRunner from "./experiment/ExperimentRunner";
import DebriefScreen from "./components/DebriefScreen";
import CompletionScreen from "./components/CompletionScreen";

const App: FC = () => {
  const state = useExperimentStore((s) => s.experimentState);
  const setState = useExperimentStore((s) => s.setExperimentState);
  const participantId = useExperimentStore((s) => s.participantId);
  const sessionId = useExperimentStore((s) => s.sessionId);
  const setParticipant = useExperimentStore((s) => s.setParticipant);
  const studyConfig = useExperimentStore((s) => s.studyConfig);
  const setStudyConfig = useExperimentStore((s) => s.setStudyConfig);
  const condition = useExperimentStore((s) => s.condition);
  const setCondition = useExperimentStore((s) => s.setCondition);
  const totalPoints = useExperimentStore((s) => s.totalPoints);
  const resumeFromTrial = useExperimentStore((s) => s.resumeFromTrial);
  const setResumeFromTrial = useExperimentStore((s) => s.setResumeFromTrial);

  const [completionCode, setCompletionCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);

  // Log screen transitions
  useEffect(() => {
    if (participantId && sessionId) {
      logScreenEvent({
        participant_id: participantId,
        session_id: sessionId,
        event_name: `screen_${state}`,
        metadata_json: JSON.stringify({ state }),
        timestamp: isoNow(),
      }).catch(() => {
        // Non-critical — best effort
      });
    }
  }, [state, participantId, sessionId]);

  // Generate a simple external ID (could be replaced with URL param or Prolific ID)
  const getExternalId = useCallback((): string => {
    const params = new URLSearchParams(window.location.search);
    return (
      params.get("PROLIFIC_PID") ??
      params.get("participant_id") ??
      params.get("id") ??
      `anon_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    );
  }, []);

  const handleConsent = useCallback(async () => {
    setRegistering(true);
    setError(null);
    try {
      const viewport = getViewportSize();
      const resp = await registerParticipant({
        external_id: getExternalId(),
        user_agent: getUserAgent(),
        viewport_width: viewport.width,
        viewport_height: viewport.height,
        timezone_offset: getTimezoneOffset(),
      });

      setParticipant(resp.participant_id, resp.session_id);
      setStudyConfig(resp.study_config);
      setCondition(resp.condition);
      if (resp.resume_from_trial !== null) {
        setResumeFromTrial(resp.resume_from_trial);
      }

      setState(ExperimentState.ELIGIBILITY);
    } catch (err) {
      setError(
        `Registration failed: ${err instanceof Error ? err.message : "Unknown error"}. Please refresh and try again.`,
      );
    } finally {
      setRegistering(false);
    }
  }, [getExternalId, setParticipant, setStudyConfig, setCondition, setResumeFromTrial, setState]);

  const handleEligibility = useCallback(() => {
    setState(ExperimentState.INSTRUCTIONS);
  }, [setState]);

  const handleInstructionsComplete = useCallback(() => {
    // If there's a practice phase, go to PRACTICE; otherwise RUNNING
    const hasPractice = studyConfig?.phases.some(
      (p) => p.type === "practice" && p.enabled,
    );
    setState(
      hasPractice ? ExperimentState.PRACTICE : ExperimentState.RUNNING,
    );
  }, [setState, studyConfig]);

  const handleDebrief = useCallback(async () => {
    if (!participantId) return;
    try {
      const resp = await completeExperiment({ participant_id: participantId });
      setCompletionCode(resp.completion_code);
      setState(ExperimentState.COMPLETE);
    } catch {
      setCompletionCode("ERROR_RETRIEVING_CODE");
      setState(ExperimentState.COMPLETE);
    }
  }, [participantId, setState]);

  // Compute target angle for instructions example
  const targetAngle = studyConfig
    ? studyConfig.stimulus.axis_min +
      (condition?.target_x ?? studyConfig.stimulus.target_x) *
        (studyConfig.stimulus.axis_max - studyConfig.stimulus.axis_min)
    : 90;

  return (
    <>
      {error && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            padding: "1rem",
            background: "#fecaca",
            color: "#991b1b",
            textAlign: "center",
            zIndex: 1000,
          }}
        >
          {error}
        </div>
      )}

      {state === ExperimentState.CONSENT && (
        <ConsentScreen
          onAgree={handleConsent}
        />
      )}

      {state === ExperimentState.CONSENT && registering && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 999,
          }}
        >
          <div
            style={{
              background: "#fff",
              padding: "2rem",
              borderRadius: 8,
              fontSize: "1.1rem",
            }}
          >
            Registering...
          </div>
        </div>
      )}

      {state === ExperimentState.ELIGIBILITY && (
        <EligibilityScreen onPass={handleEligibility} />
      )}

      {state === ExperimentState.INSTRUCTIONS && (
        <InstructionsScreen
          onComplete={handleInstructionsComplete}
          targetAngle={targetAngle}
        />
      )}

      {(state === ExperimentState.PRACTICE ||
        state === ExperimentState.RUNNING) &&
        studyConfig &&
        condition && (
          <ExperimentRunner
            config={studyConfig}
            condition={condition}
            resumeFrom={resumeFromTrial}
          />
        )}

      {state === ExperimentState.DEBRIEF && (
        <DebriefScreen onContinue={handleDebrief} totalPoints={totalPoints} />
      )}

      {state === ExperimentState.COMPLETE && (
        <CompletionScreen completionCode={completionCode} />
      )}
    </>
  );
};

export default App;
