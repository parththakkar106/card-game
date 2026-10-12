// The room connection. It applies each server message to local state and
// holds no game rules: the server decides what is valid.
import { useEffect, useReducer, useRef, useCallback } from "react";
import { capture } from "./motion.js";

const initial = { room: null, game: null, seconds: null, error: null, closed: null, reactions: [], drew: null };

function reduce(s, msg) {
  const g = s.game;
  switch (msg.type) {
    case "snapshot":
      return { ...s, room: msg.room, game: msg.game, seconds: msg.seconds, error: null, closed: null };
    case "room":
      return { ...s, room: msg, error: null };
    case "moved": {
      let table = g.table.filter((x) => !msg.removed.includes(x.id));
      for (const grp of msg.groups) {
        const i = table.findIndex((x) => x.id === grp.id);
        table = i < 0 ? [...table, grp] : table.map((x) => (x.id === grp.id ? grp : x));
      }
      let hand = g.hand;
      if (hand && msg.seat === s.room.you) {
        if (msg.to === "hand") hand = [...hand, msg.card];
        else if (msg.from === "hand") hand = hand.filter((c) => c !== msg.card);
      }
      return { ...s, game: { ...g, table, hand, counts: msg.counts }, error: null };
    }
    case "table":
      return { ...s, game: { ...g, table: msg.table, counts: msg.counts } };
    case "hand":
      return { ...s, game: { ...g, hand: msg.hand }, drew: msg.drew };
    case "turn":
      return {
        ...s,
        game: { ...g, table: msg.table, counts: msg.counts, turn: msg.turn, turn_no: msg.turn_no, pile: msg.pile, result: msg.result },
        seconds: msg.seconds,
        error: null,
        last: msg.last,
      };
    case "error":
      return { ...s, error: { ...msg, at: Date.now() } };
    case "react":
      return { ...s, reactions: [...s.reactions.slice(-8), { ...msg, key: Math.random() }] };
    case "closed":
      return { ...s, closed: msg.code };
    case "tick":
      return s.seconds ? { ...s, seconds: s.seconds - 1 } : s;
    default:
      return s;
  }
}

// These messages move cards, so the motion layer records card positions
// before React renders them.
const MOVES = new Set(["snapshot", "moved", "table", "hand", "turn"]);

export function useRoom(code) {
  const [state, dispatch] = useReducer(reduce, initial);
  const ws = useRef(null);

  useEffect(() => {
    let stop = false;
    let retry = null;
    let ping = null;
    const open = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const sock = new WebSocket(`${proto}://${location.host}/ws/${code}`);
      ws.current = sock;
      sock.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (MOVES.has(msg.type)) capture();
        dispatch(msg);
      };
      sock.onclose = (e) => {
        clearInterval(ping);
        // 4001: no name. 4002: opened in another tab. 4004: no such room.
        if (stop || [4001, 4002, 4004].includes(e.code)) {
          dispatch({ type: "closed", code: e.code });
          return;
        }
        dispatch({ type: "closed", code: "retry" });
        retry = setTimeout(open, 1500);
      };
      sock.onopen = () => {
        ping = setInterval(() => sock.send(JSON.stringify({ type: "ping" })), 20000);
      };
    };
    open();
    const timer = setInterval(() => dispatch({ type: "tick" }), 1000);
    return () => {
      stop = true;
      clearTimeout(retry);
      clearInterval(ping);
      clearInterval(timer);
      ws.current?.close();
    };
  }, [code]);

  const send = useCallback((msg) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(msg));
  }, []);

  return [state, send];
}
