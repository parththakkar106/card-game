import { useState } from "react";

const DECKS = [1, 2, 3];
const HANDS = [7, 8, 9, 10, 11, 12, 13, 14, 15];
const TIMERS = [30, 60, 90, 0];

function Pick({ label, value, options, show = (v) => v, disabled, onChange }) {
  return (
    <label className="pick">
      <span>{label}</span>
      <select value={value} disabled={disabled} onChange={(e) => onChange(Number(e.target.value))}>
        {options.map((o) => (
          <option key={o} value={o}>{show(o)}</option>
        ))}
      </select>
    </label>
  );
}

export function Lobby({ state, send }) {
  const { room, error } = state;
  const me = room.seats[room.you];
  const host = me?.host;
  const link = `${location.origin}/r/${room.code}`;
  const [copied, setCopied] = useState(false);
  const set = (key) => (v) => send({ type: "settings", [key]: v });
  const others = room.seats.filter((s) => !s.host);
  const allReady = room.seats.length >= 2 && others.every((s) => s.ready);

  return (
    <section className="panel lobby">
      <h1 className="code">ROOM {room.code}</h1>
      <div className="share">
        <input readOnly value={link} aria-label="Share link" onFocus={(e) => e.target.select()} />
        <button
          className="btn"
          onClick={() => navigator.clipboard?.writeText(link).then(() => setCopied(true))}
        >
          {copied ? "Copied" : "Copy link"}
        </button>
      </div>

      <h2>PLAYERS {room.seats.length}/10</h2>
      <ol className="lobby-seats">
        {room.seats.map((s, i) => (
          <li key={i} className={s.online ? "" : "away"}>
            <span>{s.name}{i === room.you ? " (you)" : ""}</span>
            <span className="tag">{s.host ? "HOST" : s.ready ? "READY" : s.online ? "NOT READY" : "AWAY"}</span>
          </li>
        ))}
      </ol>
      {me === undefined && <p>The room is full. You are watching.</p>}

      <h2>SETTINGS</h2>
      <div className="settings">
        <Pick label="Decks" value={room.settings.decks} options={DECKS} disabled={!host} onChange={set("decks")} />
        <Pick label="Cards each" value={room.settings.hand} options={HANDS} disabled={!host} onChange={set("hand")} />
        <Pick label="Turn timer" value={room.settings.timer} options={TIMERS} show={(t) => (t ? `${t} s` : "No limit")} disabled={!host} onChange={set("timer")} />
      </div>

      <div className="controls">
        {me && !host && (
          <button className="btn" onClick={() => send({ type: "ready", ready: !me.ready })}>
            {me.ready ? "Not ready" : "Ready"}
          </button>
        )}
        {host && (
          <button className="btn" disabled={!allReady} onClick={() => send({ type: "start" })}>
            Start game
          </button>
        )}
        <span className={`msg${error ? " err" : ""}`}>
          {error ? error.message : host ? (allReady ? "Everyone is ready." : "Waiting for players to ready up.") : "The host starts the game."}
        </span>
      </div>
    </section>
  );
}
