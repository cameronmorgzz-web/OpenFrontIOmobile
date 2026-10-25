/**
 * Battery-saver frame pacing for the in-game WebGL loop.
 *
 * The simulation only advances at ~10Hz, so between ticks most frames redraw
 * a near-identical map. While the player is interacting (touching, panning,
 * zooming, typing) every frame draws, so input stays as smooth as before;
 * once idle, frames are capped at IDLE_FPS. Phones spend most of a match idle
 * between taps, which roughly halves GPU work and heat on a 60Hz screen
 * without changing what's drawn.
 */
export const IDLE_FPS = 30;
const IDLE_FRAME_INTERVAL_MS = 1000 / IDLE_FPS;
/** How long full-rate drawing continues after the last interaction. */
export const ACTIVE_HOLD_MS = 750;
// RAF timestamps jitter by a millisecond or two; without slack a 60Hz frame
// landing at 32.9ms would be skipped and the idle rate would drop to 20fps.
const SLACK_MS = 4;

export class FramePacer {
  private lastDrawMs = Number.NEGATIVE_INFINITY;
  private activeUntilMs = Number.NEGATIVE_INFINITY;

  constructor(private readonly enabled: () => boolean) {}

  /** Keep drawing at full rate for ACTIVE_HOLD_MS from nowMs. */
  markActive(nowMs: number): void {
    this.activeUntilMs = Math.max(this.activeUntilMs, nowMs + ACTIVE_HOLD_MS);
  }

  /** Whether the frame at nowMs should draw; records it if so. */
  shouldDraw(nowMs: number): boolean {
    if (
      !this.enabled() ||
      nowMs < this.activeUntilMs ||
      nowMs - this.lastDrawMs >= IDLE_FRAME_INTERVAL_MS - SLACK_MS
    ) {
      this.lastDrawMs = nowMs;
      return true;
    }
    return false;
  }
}
