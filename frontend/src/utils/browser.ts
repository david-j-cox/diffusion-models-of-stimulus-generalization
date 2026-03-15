/**
 * Browser detection utilities.
 */

export function isMobile(): boolean {
  if (typeof navigator === "undefined") return false;
  return /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent,
  );
}

export function hasKeyboard(): boolean {
  // Best heuristic: non-mobile devices have keyboards.
  // Also check for coarse-only pointer which indicates touch-only.
  if (typeof window === "undefined") return true;
  if (isMobile()) return false;
  if (window.matchMedia && window.matchMedia("(pointer: coarse)").matches) {
    // Could be a tablet with keyboard, but assume no
    if (!window.matchMedia("(pointer: fine)").matches) return false;
  }
  return true;
}

export function getViewportSize(): { width: number; height: number } {
  return {
    width: window.innerWidth,
    height: window.innerHeight,
  };
}

export function getUserAgent(): string {
  return navigator.userAgent;
}

export function getTimezoneOffset(): number {
  return new Date().getTimezoneOffset();
}
