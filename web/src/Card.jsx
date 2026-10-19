import { useLayoutEffect, useRef } from "react";
import { face } from "./cards.js";
import { makeDraggable } from "./motion.js";

// A small stable angle per card id, so a card keeps its tilt as it moves.
const tiltOf = (id) => ((id * 7) % 5) - 2;

export function Card({ id, down = false, draggable = false, selected = false, fresh = false, onDrop, onTap }) {
  const ref = useRef(null);
  // Draggable keeps the handlers it was created with, so read the latest
  // props through a ref.
  const props = useRef({ onDrop, onTap });
  props.current = { onDrop, onTap };

  useLayoutEffect(() => {
    if (!draggable) return;
    return makeDraggable(ref.current, {
      onDrop: (zone) => props.current.onDrop?.(id, zone, ref.current),
      onClick: () => props.current.onTap?.(id),
    });
  }, [draggable, id]);

  if (down) return <div className="card down" aria-label="Face-down card" />;
  const f = face(id);
  return (
    <div
      ref={ref}
      className={`card${f.red ? " red" : ""}${draggable ? " grab" : ""}${selected ? " sel" : ""}${fresh ? " fresh" : ""}`}
      data-flip-id={`c${id}`}
      data-card={id}
      style={{ "--k": tiltOf(id) }}
      role="img"
      aria-label={f.label}
      onClick={draggable ? undefined : () => onTap?.(id)}
    >
      <span className="ix">{f.rank}<i>{f.suit}</i></span>
      <span className="pip">{f.suit}</span>
      <span className="ix br">{f.rank}<i>{f.suit}</i></span>
    </div>
  );
}
