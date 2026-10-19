import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Card } from "./Card.jsx";
import { sortHand } from "./cards.js";
import { layout, useWide } from "./board.js";
import { play, pop, shake, snapBack } from "./motion.js";

function Seats({ room, game, reactions }) {
  return (
    <div className="seats">
      {room.seats.map((s, i) => (
        <div key={i} className={`seat${game.turn === i && !game.result ? " turn" : ""}${s.online ? "" : " away"}`}>
          <span className="av">{s.name.slice(0, 2).toUpperCase()}</span>
          <span className="who">
            {s.name}
            {i === room.you ? " (you)" : ""}
          </span>
          <span className="n">{game.counts[i]}</span>
          {reactions.filter((r) => r.seat === i).slice(-1).map((r) => (
            <Burst key={r.key} emoji={r.emoji} />
          ))}
        </div>
      ))}
    </div>
  );
}

function Burst({ emoji }) {
  const ref = useRef(null);
  const [gone, setGone] = useState(false);
  useLayoutEffect(() => pop(ref.current), []);
  useEffect(() => {
    const t = setTimeout(() => setGone(true), 1800);
    return () => clearTimeout(t);
  }, []);
  return gone ? null : <span ref={ref} className="burst">{emoji}</span>;
}

function status(state, mine) {
  const { room, game, last } = state;
  const name = (i) => room.seats[i]?.name ?? `Seat ${i + 1}`;
  if (game.result) return game.result.winner === null ? "The pile ran out and everyone passed. No winner." : `${name(game.result.winner)} wins!`;
  const before = last
    ? { played: `${name(last.seat)} played. `, drew: `${name(last.seat)} drew. `, passed: `${name(last.seat)} passed. `, timeout: `${name(last.seat)} ran out of time. ` }[last.how]
    : "";
  if (mine) return `${before}Your turn. Move cards, then end your turn, or draw.`;
  return `${before}${name(game.turn)} is playing.`;
}

const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function savedSort() {
  try {
    return localStorage.getItem("sort") ?? "suit";
  } catch {
    return "suit";
  }
}

export function Table({ state, send }) {
  const { room, game, seconds, error, reactions, drew } = state;
  const you = room.you;
  const mine = you !== null && game.turn === you && !game.result;
  const [selected, setSelected] = useState(null);
  const pending = useRef(null);
  const msgRef = useRef(null);
  const wide = useWide();
  const boardRef = useRef(null);
  const pos = useRef({});
  const newAt = useRef(null);
  const [sortBy, setSortBy] = useState(savedSort);

  const changeSort = (by) => {
    setSortBy(by);
    try {
      localStorage.setItem("sort", by);
    } catch {
      // Private windows can block storage. The choice still applies until reload.
    }
  };

  // Show the turn in the tab title, so a player in another tab sees it.
  useEffect(() => {
    if (!mine) return;
    const before = document.title;
    document.title = "▶ Your turn · Card Game";
    return () => {
      document.title = before;
    };
  }, [mine]);

  // Place groups before the cards animate, so each card flies to its final spot.
  useLayoutEffect(() => {
    if (!wide) {
      boardRef.current.style.removeProperty("--fill");
      return;
    }
    layout(boardRef.current, pos.current, newAt.current);
    newAt.current = null;
  }, [game, wide]);

  // Animate cards after every change the server sends.
  useLayoutEffect(() => {
    play();
  }, [game]);

  useEffect(() => {
    if (!error) return;
    if (error.about === "move") snapBack(pending.current);
    pending.current = null;
    shake(msgRef.current);
  }, [error]);

  useEffect(() => setSelected(null), [game.turn]);

  const where = (card) => {
    if (game.hand?.includes(card)) return "hand";
    return game.table.find((g) => g.cards.includes(card))?.id;
  };

  const moveTo = (card, to, el) => {
    if (to === undefined || to === where(card)) {
      snapBack(el);
      return;
    }
    pending.current = el;
    if (wide && to === "new" && el) {
      const b = boardRef.current.getBoundingClientRect();
      const r = el.getBoundingClientRect();
      newAt.current = { card, x: Math.max(0, r.left - b.left - 12), y: Math.max(0, r.top - b.top - 12) };
    }
    send({ type: "move", card, to });
  };

  const zoneValue = (zone) => {
    const v = zone?.dataset.drop;
    if (v === undefined) return undefined;
    return v === "hand" || v === "new" ? v : Number(v);
  };

  const onDrop = (card, zone, el) => moveTo(card, zoneValue(zone), el);
  const onTap = (card) => setSelected((s) => (s === card ? null : card));
  const tapZone = (to) => (e) => {
    if (selected === null || e.target.closest("[data-card]")) return;
    moveTo(selected, to, null);
    setSelected(null);
  };

  // On the free board, a tap on empty felt starts a new group at that spot.
  const tapBoard = (e) => {
    if (selected === null || e.target !== e.currentTarget) return;
    const b = e.currentTarget.getBoundingClientRect();
    newAt.current = { card: selected, x: Math.max(0, e.clientX - b.left - 30), y: Math.max(0, e.clientY - b.top - 30) };
    tapZone("new")(e);
  };

  // Drag a group by its handle. Only this player's screen changes.
  const moveGroup = (id) => (e) => {
    e.preventDefault();
    const el = e.currentTarget.parentElement;
    const p = pos.current[id];
    const [sx, sy, ox, oy] = [e.clientX, e.clientY, p.x, p.y];
    el.classList.add("moving");
    const onMove = (ev) => {
      p.x = Math.max(0, ox + ev.clientX - sx);
      p.y = Math.max(0, oy + ev.clientY - sy);
      el.style.left = `${p.x}px`;
      el.style.top = `${p.y}px`;
    };
    const onUp = () => {
      el.classList.remove("moving");
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      layout(boardRef.current, pos.current, null);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const tidy = () => {
    pos.current = {};
    layout(boardRef.current, pos.current, null);
  };

  const timer = seconds === null ? "∞" : clock(seconds);
  const isHost = room.seats[you]?.host;

  return (
    <section className="stage">
      <div className="bar">
        <Seats room={room} game={game} reactions={reactions} />
        <div className={`timer${seconds !== null && seconds <= 10 ? " low" : ""}`} aria-label="Time left">
          {timer}
        </div>
      </div>

      <div
        ref={boardRef}
        className={`table${wide ? " free" : ""}`}
        data-drop={wide && mine ? "new" : undefined}
        onClick={wide && mine ? tapBoard : undefined}
      >
        {game.table.map((g) => (
          <div key={g.id} className={`group ${g.valid ? "ok" : "bad"}`} data-why={g.why ?? undefined} data-gid={g.id} data-drop={mine ? g.id : undefined} onClick={mine ? tapZone(g.id) : undefined}>
            {wide && (
              <span className="grip" aria-label="Move this group" onPointerDown={moveGroup(g.id)} onClick={(e) => e.stopPropagation()}>
                ⠿ Move
              </span>
            )}
            {g.cards.map((c) => (
              <Card key={c} id={c} draggable={mine} selected={selected === c} onDrop={onDrop} onTap={onTap} />
            ))}
          </div>
        ))}
        {mine && !wide && (
          <div className="group new" data-drop="new" onClick={tapZone("new")}>
            Drop here to start a new group
          </div>
        )}
        {!game.table.length && !mine && <p className="empty">The table is empty. The first play must be runs only.</p>}
      </div>

      <div className="controls">
        {mine && (
          <>
            <button className="btn" onClick={() => send({ type: "end_turn" })}>End turn</button>
            <button className="btn ghost" onClick={() => send({ type: "reset" })}>Reset</button>
            <button className="btn danger" onClick={() => send({ type: "draw" })}>{game.pile ? "Draw" : "Pass"}</button>
          </>
        )}
        {wide && game.table.length > 0 && <button className="btn ghost" onClick={tidy}>Tidy board</button>}
        <span ref={msgRef} className={`msg${error ? " err" : ""}`} aria-live="polite">
          {error ? error.message : status(state, mine)}
        </span>
      </div>

      <div className="lower">
        <div className="pile" aria-label={`Draw pile, ${game.pile} cards`}>
          {game.pile > 0 ? <Card down /> : <div className="card empty-pile" />}
          <span>{game.pile} left</span>
        </div>
        {game.hand ? (
          <div className="hand-wrap">
            <div className="sort" role="group" aria-label="Sort your hand">
              <span>Sort by</span>
              {["suit", "rank"].map((by) => (
                <button key={by} className={sortBy === by ? "on" : ""} aria-pressed={sortBy === by} onClick={() => changeSort(by)}>
                  {by === "suit" ? "Suit" : "Number"}
                </button>
              ))}
            </div>
            <div className="hand" data-drop={mine ? "hand" : undefined} onClick={mine ? tapZone("hand") : undefined} aria-label="Your hand">
              {sortHand(game.hand, sortBy).map((c) => (
                <Card key={c} id={c} draggable={mine} selected={selected === c} fresh={c === drew} onDrop={onDrop} onTap={onTap} />
              ))}
            </div>
          </div>
        ) : (
          <div className="hand watching">You are watching this game.</div>
        )}
      </div>

      {you !== null && (
        <div className="reactions" aria-label="Reactions">
          {room.reactions.map((e) => (
            <button key={e} className="react" onClick={() => send({ type: "react", emoji: e })}>{e}</button>
          ))}
        </div>
      )}

      {game.result && (
        <div className="over" role="dialog" aria-label="Game over">
          <h2>{game.result.winner === null ? "NO WINNER" : `${room.seats[game.result.winner]?.name} WINS!`}</h2>
          {isHost ? (
            <button className="btn" onClick={() => send({ type: "rematch" })}>Rematch</button>
          ) : (
            <p>Waiting for the host to start a rematch.</p>
          )}
        </div>
      )}
    </section>
  );
}
