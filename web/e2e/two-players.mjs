// Run with `npm run e2e` while the game server runs on BASE_URL (default
// http://localhost:8000). Two browser players start a game. The first player
// places a card, undoes it, places it again, and draws. The check fails if the
// other player does not see each step.
import assert from "node:assert/strict";
import { chromium } from "playwright";

const BASE = process.env.BASE_URL ?? "http://localhost:8000";
const browser = await chromium.launch();
const errors = [];

async function player(name) {
  const page = await (await browser.newContext({ viewport: { width: 1100, height: 700 } })).newPage();
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  await page.goto(BASE);
  await page.fill("input[aria-label='Your name']", name);
  await page.click("text=Continue");
  return page;
}

try {
  const ann = await player("Ann");
  const bo = await player("Bo");
  await ann.click("text=Create a room");
  await ann.waitForURL(/\/r\//);
  await bo.goto(ann.url());
  await bo.click("button:has-text('Ready')");
  await ann.click("text=Start game");
  await ann.waitForSelector(".timer");
  await bo.waitForSelector(".timer");

  // Seat 0 plays first, and the host takes seat 0.
  const hand = ann.locator(".hand [data-card]");
  assert.equal(await hand.count(), 13);
  const card = await hand.first().getAttribute("data-card");
  const place = async () => {
    await ann.locator(`.hand [data-card="${card}"]`).click();
    await ann.mouse.click(300, 200);
    await bo.waitForSelector(`.table [data-card="${card}"]`);
  };

  await place();
  assert.equal(await hand.count(), 12);
  await ann.click("button:has-text('Undo')");
  await bo.waitForSelector(`.table [data-card="${card}"]`, { state: "detached" });
  assert.equal(await hand.count(), 13);

  await place();
  await ann.click("button:has-text('Draw')");
  // A draw reverts the table, returns the card, and adds one from the pile.
  await bo.waitForSelector(".seat.turn >> text=Bo (you)");
  await ann.waitForSelector(".hand .card.fresh");
  assert.equal(await hand.count(), 14);
  assert.equal(await bo.locator(".table [data-card]").count(), 0);
  assert.equal(await bo.locator(".seat >> nth=0 >> .n").innerText(), "14");
  assert.deepEqual(errors, []);
  console.log("two-player e2e ok");
} finally {
  await browser.close();
}
