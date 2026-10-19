// Run with `node src/cards.check.mjs`. Checks both hand sort orders.
import assert from "node:assert/strict";
import { sortHand } from "./cards.js";

// 9 of hearts (21), 2 of spades (1), 9 of spades (8), ace of clubs (39).
const hand = [21, 1, 8, 39];
assert.deepEqual(sortHand(hand, "suit"), [1, 8, 21, 39]);
assert.deepEqual(sortHand(hand, "rank"), [39, 1, 8, 21]);
console.log("cards.js ok");
