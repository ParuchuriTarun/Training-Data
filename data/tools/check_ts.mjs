// Helper for check_code_blocks.py: validates TypeScript syntax with Node's built-in parser.
import { stripTypeScriptTypes } from "node:module";
import { readFileSync } from "node:fs";

const code = readFileSync(process.argv[2], "utf8");
try {
  stripTypeScriptTypes(code, { mode: "transform" });
} catch (e) {
  console.error("Error: " + String(e.message).split("\n")[0]);
  process.exit(1);
}
