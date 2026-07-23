import { describe, it, expect } from "vitest";
import { PREVIEW_QUALITY_EDGE, type PreviewQuality } from "../index";

describe("PREVIEW_QUALITY_EDGE", () => {
  it("maps all quality levels", () => {
    const expected: Record<PreviewQuality, number> = {
      low: 320,
      medium: 640,
      high: 1280,
      original: 0,
    };
    expect(PREVIEW_QUALITY_EDGE).toEqual(expected);
  });

  it("low is 320", () => {
    expect(PREVIEW_QUALITY_EDGE.low).toBe(320);
  });

  it("medium is 640", () => {
    expect(PREVIEW_QUALITY_EDGE.medium).toBe(640);
  });

  it("high is 1280", () => {
    expect(PREVIEW_QUALITY_EDGE.high).toBe(1280);
  });

  it("original is 0 (no resize)", () => {
    expect(PREVIEW_QUALITY_EDGE.original).toBe(0);
  });
});
