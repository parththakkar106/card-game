// Run with `node src/board.check.mjs`. Checks that `spread` moves a group off
// another group, and wraps it to the next row at the board's right edge.
import assert from "node:assert/strict";
import { spread } from "./board.js";

const box = (x, y) => ({ p: { x, y }, w: 100, h: 80 });
const a = box(16, 16), b = box(50, 20);
spread([a, b], 1000);
assert.deepEqual(b.p, { x: 142, y: 20 });

const c = box(16, 16), d = box(20, 16);
spread([c, d], 200);
assert.deepEqual(d.p, { x: 16, y: 122 });
console.log("board.js ok");
