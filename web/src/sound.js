// Short sound effects made with the Web Audio API, so the game ships no audio
// files. Each sound is a list of notes: [frequency in Hz, start s, length s].
const SOUNDS = {
  place: [[520, 0, 0.05]],
  draw: [[330, 0, 0.07], [440, 0.06, 0.07]],
  turn: [[660, 0, 0.1], [880, 0.1, 0.14]],
  error: [[180, 0, 0.12], [140, 0.1, 0.14]],
  win: [[523, 0, 0.12], [659, 0.12, 0.12], [784, 0.24, 0.12], [1047, 0.36, 0.3]],
};

let ctx = null;
let muted = false;
try {
  muted = localStorage.getItem("muted") === "1";
} catch {
  // Private windows can block storage. Sound stays on.
}

export const isMuted = () => muted;

export function setMuted(value) {
  muted = value;
  try {
    localStorage.setItem("muted", value ? "1" : "0");
  } catch {
    // The choice still applies until reload.
  }
}

export function sound(name) {
  if (muted) return;
  // Browsers allow audio only after the player has clicked the page.
  ctx ??= new AudioContext();
  if (ctx.state === "suspended") ctx.resume();
  const t = ctx.currentTime;
  for (const [hz, at, len] of SOUNDS[name]) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "triangle";
    osc.frequency.value = hz;
    gain.gain.setValueAtTime(0.15, t + at);
    gain.gain.exponentialRampToValueAtTime(0.001, t + at + len);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t + at);
    osc.stop(t + at + len);
  }
}
