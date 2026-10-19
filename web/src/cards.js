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

// Sort by suit groups each suit in rank order. Sort by rank puts equal ranks
// side by side, which helps you spot sets.
export function sortHand(hand, by = "suit") {
  const key = (id) => (by === "rank" ? (id % 13) * 4 + Math.floor((id % 52) / 13) : face(id).order);
  return [...hand].sort((a, b) => key(a) - key(b) || a - b);
}
