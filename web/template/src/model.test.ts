import { describe, expect, it } from "vitest";
import {
  canSubmit,
  fleet,
  isLocked,
  scenarios,
  type CommandState,
} from "./model";
describe("supervisory command guards", () => {
  it.each(["lost", "recovery", "truth"] as const)(
    "locks commands in %s",
    (scenario) => {
      expect(isLocked(scenario)).toBe(true);
      expect(canSubmit(scenario, "idle")).toBe(false);
      expect(canSubmit(scenario, "review")).toBe(false);
    },
  );
  it.each([
    "pending",
    "accepted",
    "unconfirmed",
    "declined",
    "completed",
  ] satisfies CommandState[])("prevents resubmission from %s", (state) =>
    expect(canSubmit("monitoring", state)).toBe(false),
  );
  it("permits a reviewed proposal, not an unconfirmed retry", () => {
    expect(canSubmit("decision", "review")).toBe(true);
    expect(canSubmit("decision", "rejected")).toBe(true);
    expect(canSubmit("decision", "unconfirmed")).toBe(false);
  });
  it("keeps the synthetic fleet and scenario identifiers stable", () => {
    expect(fleet).toHaveLength(5);
    expect(new Set(fleet.map((b) => b.id)).size).toBe(5);
    expect(scenarios).toHaveLength(9);
  });
});
