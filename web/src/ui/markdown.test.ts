import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { Markdown } from "./Markdown";

const render = (text: string) => Markdown({ text }) as ReturnType<typeof createElement>;
const children = (text: string) => (render(text).props as { children: unknown[] }).children;

describe("Markdown", () => {
  it("does not hang on a table row with no separator under it (crashed Help)", () => {
    const out = children("| a | b |\n\n| **x** | y |\n\n## Next");
    expect(out.length).toBe(3);
  });
  it("still renders a real table, lists and headings", () => {
    const out = children("# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n- one\n- two\n\ntext");
    expect(out.length).toBe(4);
  });
});
