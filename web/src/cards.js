// Card ids come from the server. This file only turns an id into what to
// draw. It holds no game rules.
const RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"];
const SUITS = ["♠", "♥", "♦", "♣"];
const NAMES = ["spades", "hearts", "diamonds", "clubs"];

export function face(id) {
  const r = id % 13;
  const s = Math.floor((id % 52) / 13);
  return { rank: RANKS[r], suit: SUITS[s], red: s === 1 || s === 2, label: `${RANKS[r]} of ${NAMES[s]}`, order: s * 13 + r };
}

// The hand shows suits together, then ranks in order.
export function sortHand(hand) {
  return [...hand].sort((a, b) => face(a).order - face(b).order || a - b);
}
