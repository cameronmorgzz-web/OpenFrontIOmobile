import { describe, expect, it } from "vitest";
import { ACTIVE_HOLD_MS, FramePacer } from "../../src/client/FramePacer";

const FRAME_60HZ = 1000 / 60;
const FRAME_120HZ = 1000 / 120;

function drawnFrames(pacer: FramePacer, frameMs: number, count: number) {
  let drawn = 0;
  for (let i = 1; i <= count; i++) {
    if (pacer.shouldDraw(i * frameMs)) drawn++;
  }
  return drawn;
}

describe("FramePacer", () => {
  it("draws every frame when battery saver is off", () => {
    expect(drawnFrames(new FramePacer(() => false), FRAME_60HZ, 60)).toBe(60);
  });

  it("halves an idle 60Hz display to 30fps", () => {
    expect(drawnFrames(new FramePacer(() => true), FRAME_60HZ, 60)).toBe(30);
  });

  it("caps an idle 120Hz display at 30fps", () => {
    expect(drawnFrames(new FramePacer(() => true), FRAME_120HZ, 120)).toBe(30);
  });

  it("tolerates RAF jitter instead of dropping to 20fps", () => {
    const pacer = new FramePacer(() => true);
    expect(pacer.shouldDraw(0)).toBe(true);
    expect(pacer.shouldDraw(16.2)).toBe(false);
    expect(pacer.shouldDraw(32.4)).toBe(true);
  });

  it("draws every frame while the player is interacting", () => {
    const pacer = new FramePacer(() => true);
    pacer.markActive(0);
    const framesInHold = Math.floor(ACTIVE_HOLD_MS / FRAME_60HZ) - 1;
    expect(drawnFrames(pacer, FRAME_60HZ, framesInHold)).toBe(framesInHold);
  });

  it("returns to the idle rate once the hold expires", () => {
    const pacer = new FramePacer(() => true);
    pacer.markActive(0);
    let drawn = 0;
    const start = Math.ceil(ACTIVE_HOLD_MS / FRAME_60HZ) + 1;
    for (let i = start; i < start + 60; i++) {
      if (pacer.shouldDraw(i * FRAME_60HZ)) drawn++;
    }
    expect(drawn).toBe(30);
  });
});
