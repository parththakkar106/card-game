// The free board on wide screens. Each player arranges groups on their own
// screen, so group positions live only in the browser and never reach the
// server. Narrow screens keep the wrapping row layout.
import { useEffect, useState } from "react";

const WIDE = "(min-width: 900px)";

export function useWide() {
  const [wide, setWide] = useState(() => window.matchMedia(WIDE).matches);
  useEffect(() => {
    const m = window.matchMedia(WIDE);
    const update = () => setWide(m.matches);
    m.addEventListener("change", update);
    return () => m.removeEventListener("change", update);
  }, []);
  return wide;
}

const GAP = 26;
const EDGE = 16;

// Place every group on the board. `pos` maps a group id to `{x, y}` and keeps
// positions between renders. If `pending` names the card that just started a
// new group, that group goes where the player dropped the card.
export function layout(board, pos, pending) {
  const els = [...board.querySelectorAll(".group[data-gid]")];
  const live = new Set(els.map((el) => el.dataset.gid));
  for (const id of Object.keys(pos)) if (!live.has(id)) delete pos[id];

  const items = els.map((el) => {
    const id = el.dataset.gid;
    if (!pos[id]) {
      const here = pending && el.querySelector(`[data-card="${pending.card}"]`);
      pos[id] = here ? { x: pending.x, y: pending.y } : { x: EDGE, y: EDGE };
    }
    return { el, p: pos[id], w: el.offsetWidth, h: el.offsetHeight };
  });
  spread(items, board.clientWidth);

  let bottom = 0;
  for (const { el, p, h } of items) {
    el.style.left = `${p.x}px`;
    el.style.top = `${p.y}px`;
    bottom = Math.max(bottom, p.y + h);
  }
  board.style.setProperty("--fill", `${bottom + 40}px`);
}

// Push a group right, or down to the next row, when another group covers it.
// Groups are visited top to bottom, so a group never pushes one above it.
export function spread(items, width) {
  const sorted = [...items].sort((a, b) => a.p.y - b.p.y || a.p.x - b.p.x);
  for (let i = 0; i < sorted.length; i++) {
    const b = sorted[i];
    for (let j = 0; j < i; j++) {
      const a = sorted[j];
      const overlap = b.p.x < a.p.x + a.w + 10 && a.p.x < b.p.x + b.w + 10 && b.p.y < a.p.y + a.h + 10 && a.p.y < b.p.y + b.h + 10;
      if (!overlap) continue;
      b.p.x = a.p.x + a.w + GAP;
      if (b.p.x + b.w > width - EDGE) {
        b.p.x = EDGE;
        b.p.y = a.p.y + a.h + GAP;
      }
      j = -1;
    }
  }
}
