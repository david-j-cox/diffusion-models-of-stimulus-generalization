/**
 * API client for the stimulus generalization experiment backend.
 */

import type { TrialResult, StudyConfig, ConditionAssignment } from "../experiment/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

interface RegisterResponse {
  participant_id: string;
  session_id: string;
  condition: ConditionAssignment;
  study_config: StudyConfig;
  resume_from_trial: number | null;
}

interface BatchResponse {
  saved_count: number;
  next_expected_trial: number;
}

interface CompleteResponse {
  completion_code: string;
}

async function request<T>(
  path: string,
  body: unknown,
  retries = 0,
  retryDelayMs = 1000,
): Promise<T> {
  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const resp = await fetch(`${API_BASE}/api${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`API ${path} returned ${resp.status}: ${text}`);
      }
      return (await resp.json()) as T;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, retryDelayMs * (attempt + 1)));
      }
    }
  }
  throw lastError!;
}

export async function registerParticipant(params: {
  external_id: string;
  user_agent: string;
  viewport_width: number;
  viewport_height: number;
  timezone_offset: number;
}): Promise<RegisterResponse> {
  return request<RegisterResponse>("/participants/register", params);
}

export async function submitTrialBatch(params: {
  participant_id: string;
  session_id: string;
  trials: TrialResult[];
}): Promise<BatchResponse> {
  // Retry up to 3 times for trial data — we don't want to lose responses.
  return request<BatchResponse>("/trials/batch", params, 3, 1500);
}

export async function logScreenEvent(params: {
  participant_id: string;
  session_id: string;
  event_name: string;
  metadata_json: string;
  timestamp: string;
}): Promise<void> {
  await request<unknown>("/participants/screen-event", params);
}

export async function completeExperiment(params: {
  participant_id: string;
}): Promise<CompleteResponse> {
  return request<CompleteResponse>("/participants/complete", params);
}

/**
 * Best-effort flush using sendBeacon (for beforeunload).
 * Falls back to sync-ish fetch.
 */
export function flushTrialBatchBeacon(params: {
  participant_id: string;
  session_id: string;
  trials: TrialResult[];
}): void {
  const url = `${API_BASE}/api/trials/batch`;
  const blob = new Blob([JSON.stringify(params)], {
    type: "application/json",
  });
  if (navigator.sendBeacon) {
    navigator.sendBeacon(url, blob);
  } else {
    // Last-resort synchronous-ish attempt
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
      keepalive: true,
    }).catch(() => {
      // Nothing we can do
    });
  }
}
