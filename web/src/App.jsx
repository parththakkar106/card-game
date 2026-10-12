import { useEffect, useState } from "react";
import { Lobby } from "./Lobby.jsx";
import { Table } from "./Table.jsx";
import { useRoom } from "./useRoom.js";

const roomCode = () => location.pathname.match(/^\/r\/([A-Za-z0-9]+)/)?.[1]?.toUpperCase() ?? null;

async function post(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail ?? "Something went wrong.");
  return data;
}

function NameForm({ onDone, current }) {
  const [name, setName] = useState(current ?? "");
  const [error, setError] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    try {
      onDone((await post("/api/me", { name })).name);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <form className="panel" onSubmit={submit}>
      <h2>WHAT SHOULD WE CALL YOU?</h2>
      <input value={name} onChange={(e) => setName(e.target.value)} maxLength={16} pattern="[A-Za-z0-9_\- ]{2,16}" required autoFocus aria-label="Your name" />
      <button className="btn">Continue</button>
      {error && <p className="msg err">{error}</p>}
    </form>
  );
}

function Home({ name, onRename }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const create = async () => {
    try {
      const { code } = await post("/api/rooms");
      location.assign(`/r/${code}`);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <section className="panel home">
      <p>
        Playing as <b>{name}</b>. <button className="link" onClick={onRename}>Change</button>
      </p>
      <button className="btn big" onClick={create}>Create a room</button>
      <form className="join" onSubmit={(e) => (e.preventDefault(), location.assign(`/r/${code.trim().toUpperCase()}`))}>
        <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Room code" maxLength={5} aria-label="Room code" required />
        <button className="btn ghost">Join</button>
      </form>
      {error && <p className="msg err">{error}</p>}
    </section>
  );
}

const CLOSED = {
  4004: "That room doesn't exist. It may have closed after a while with nobody in it.",
  4002: "You opened this room in another tab.",
  4001: "Pick a name first.",
};

function Room({ code }) {
  const [state, send] = useRoom(code);
  if (state.closed && state.closed !== "retry") {
    return (
      <section className="panel">
        <p>{CLOSED[state.closed]}</p>
        <a className="btn" href="/">Home</a>
      </section>
    );
  }
  if (!state.room) return <p className="loading">Connecting…</p>;
  return (
    <>
      {state.closed === "retry" && <p className="banner">Reconnecting…</p>}
      {state.room.phase === "lobby" ? <Lobby state={state} send={send} /> : <Table state={state} send={send} />}
    </>
  );
}

export function App() {
  const [name, setName] = useState(undefined);
  const [renaming, setRenaming] = useState(false);
  const code = roomCode();
  useEffect(() => {
    fetch("/api/me").then((r) => r.json()).then((d) => setName(d.name ?? null));
  }, []);

  let body;
  if (name === undefined) body = <p className="loading">Loading…</p>;
  else if (!name || renaming) body = <NameForm current={name} onDone={(n) => (setName(n), setRenaming(false))} />;
  else if (code) body = <Room code={code} />;
  else body = <Home name={name} onRename={() => setRenaming(true)} />;

  return (
    <main>
      <header className="top">
        <a href="/" className="logo">CARD GAME</a>
      </header>
      {body}
    </main>
  );
}
