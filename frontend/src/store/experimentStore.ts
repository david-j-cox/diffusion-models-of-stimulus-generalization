import { create } from "zustand";
import {
  ExperimentState,
  type StudyConfig,
  type ConditionAssignment,
} from "../experiment/types";

interface ExperimentStore {
  experimentState: ExperimentState;
  participantId: string | null;
  sessionId: string | null;
  studyConfig: StudyConfig | null;
  condition: ConditionAssignment | null;
  totalPoints: number;
  resumeFromTrial: number | null;

  setExperimentState: (state: ExperimentState) => void;
  setParticipant: (participantId: string, sessionId: string) => void;
  setStudyConfig: (config: StudyConfig) => void;
  setCondition: (condition: ConditionAssignment) => void;
  addPoints: (n: number) => void;
  setResumeFromTrial: (idx: number | null) => void;
}

export const useExperimentStore = create<ExperimentStore>((set) => ({
  experimentState: ExperimentState.CONSENT,
  participantId: null,
  sessionId: null,
  studyConfig: null,
  condition: null,
  totalPoints: 0,
  resumeFromTrial: null,

  setExperimentState: (experimentState) => set({ experimentState }),
  setParticipant: (participantId, sessionId) =>
    set({ participantId, sessionId }),
  setStudyConfig: (studyConfig) => set({ studyConfig }),
  setCondition: (condition) => set({ condition }),
  addPoints: (n) => set((s) => ({ totalPoints: s.totalPoints + n })),
  setResumeFromTrial: (resumeFromTrial) => set({ resumeFromTrial }),
}));
