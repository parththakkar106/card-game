// All card motion lives in this file. The game code calls these functions and
// never calls GSAP directly, so you can retune or replace the animation
// library here without touching the game logic.
import { gsap } from "gsap";
import { Flip } from "gsap/Flip";
import { Draggable } from "gsap/Draggable";

gsap.registerPlugin(Flip, Draggable);

export const settings = {
  duration: 0.5,
  ease: "back.out(1.6)",
  back: "power2.out",
  enterStagger: 0.04,
};

const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const CARDS = "[data-flip-id]";
let saved = null;

// Record where every card is. Call this just before a state change moves
// cards, then call `play` after React renders the change.
export function capture() {
  saved = Flip.getState(CARDS);
}

// Animate every card from its recorded place to its new place.
export function play() {
  if (!saved) return;
  const state = saved;
  saved = null;
  // A dropped card still carries its drag offset. Clear it so the card's end
  // place is its slot, then animate from where the player let go.
  gsap.set(CARDS, { x: 0, y: 0 });
  if (reduce()) return;
  Flip.from(state, {
    targets: CARDS,
    duration: settings.duration,
    ease: settings.ease,
    nested: true,
    onEnter: (els) =>
      gsap.fromTo(els, { opacity: 0, scale: 0.6, y: -30 }, { opacity: 1, scale: 1, y: 0, duration: settings.duration, ease: settings.ease, stagger: settings.enterStagger }),
  });
}

// Send a card back to its slot after a refused or empty drop.
export function snapBack(el) {
  if (el) gsap.to(el, { x: 0, y: 0, duration: reduce() ? 0 : 0.3, ease: settings.back });
}

export function shake(el) {
  if (el && !reduce()) gsap.fromTo(el, { x: -8 }, { x: 0, duration: 0.5, ease: "elastic.out(1, 0.3)" });
}

export function pop(el) {
  if (el && !reduce()) gsap.fromTo(el, { scale: 0.3, rotation: -20, opacity: 0 }, { scale: 1, rotation: 0, opacity: 1, duration: 0.4, ease: "back.out(2.5)" });
}

// Make one card draggable. `onDrop(target)` receives the drop zone under the
// pointer: an element with a `data-drop` attribute, or null.
export function makeDraggable(el, { onPress, onDrop, onClick }) {
  const [d] = Draggable.create(el, {
    type: "x,y",
    zIndexBoost: true,
    minimumMovement: 6,
    onPress,
    onDrag() {
      highlight(dropAt(this.pointerX, this.pointerY, el));
    },
    onDragEnd() {
      highlight(null);
      onDrop(dropAt(this.pointerX, this.pointerY, el));
    },
    onClick,
  });
  return () => d.kill();
}

function dropAt(x, y, dragged) {
  for (const el of document.elementsFromPoint(x, y)) {
    if (dragged.contains(el)) continue;
    const zone = el.closest("[data-drop]");
    if (zone) return zone;
  }
  return null;
}

function highlight(zone) {
  document.querySelectorAll(".target").forEach((z) => z.classList.remove("target"));
  if (zone) zone.classList.add("target");
}
