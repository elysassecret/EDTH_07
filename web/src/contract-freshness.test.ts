import { describe, expect, it } from "vitest";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

describe("frozen-schema TypeScript generation", () => {
  it("keeps the checked-in types identical to the existing schema", () => {
    const require = createRequire(import.meta.url);
    const cli = require.resolve("json-schema-to-typescript/dist/src/cli.js");
    const generated = execFileSync(process.execPath, [cli,
      "-i", fileURLToPath(new URL("../../contract/schema.json", import.meta.url)),
      "--additionalProperties", "false", "--bannerComment",
      "// GENERATED from contract/schema.json by pnpm gen:contract. Do not edit.",
    ], { encoding: "utf8" });
    expect(readFileSync(new URL("./contract.ts", import.meta.url), "utf8")).toBe(generated);
  });
});
