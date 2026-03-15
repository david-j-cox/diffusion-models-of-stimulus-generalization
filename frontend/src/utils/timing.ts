/**
 * High-resolution timing utilities.
 */

/** Returns a monotonic high-resolution timestamp in milliseconds. */
export function now(): number {
  return performance.now();
}

/** Returns the current wall-clock time as an ISO-8601 UTC string. */
export function isoNow(): string {
  return new Date().toISOString();
}

/**
 * Returns a Promise that resolves after `ms` milliseconds,
 * driven by requestAnimationFrame for more accurate visual timing.
 */
export function rafDelay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    const start = performance.now();
    function check() {
      if (performance.now() - start >= ms) {
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    }
    requestAnimationFrame(check);
  });
}

/**
 * setTimeout-based delay. Useful for non-visual timing.
 */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
