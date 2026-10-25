// הקלטת מיקרופון גולמית (PCM) עם זיהוי סוף דיבור אוטומטי, והמרה ל-WAV מונו 16kHz.
// עובד בכל הדפדפנים המודרניים (Chrome, Edge, Safari, Firefox) בלי תלות בקודק של MediaRecorder.

const WORKLET_SRC = `
class PcmCapture extends AudioWorkletProcessor {
  constructor() { super(); this.parts = []; this.size = 0; }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) {
      this.parts.push(new Float32Array(ch));
      this.size += ch.length;
      if (this.size >= 2048) {
        const out = new Float32Array(this.size);
        let o = 0;
        for (const p of this.parts) { out.set(p, o); o += p.length; }
        this.port.postMessage(out, [out.buffer]);
        this.parts = []; this.size = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm-capture', PcmCapture);
`;

let sharedCtx = null;
let workletReady = null;

async function getContext() {
  if (!sharedCtx || sharedCtx.state === 'closed') {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    sharedCtx = new Ctx();
    workletReady = null;
  }
  if (sharedCtx.state === 'suspended') await sharedCtx.resume();
  if (!workletReady) {
    const url = URL.createObjectURL(new Blob([WORKLET_SRC], { type: 'application/javascript' }));
    workletReady = sharedCtx.audioWorklet.addModule(url).finally(() => URL.revokeObjectURL(url));
  }
  await workletReady;
  return sharedCtx;
}

export class MicError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

export async function openMicrophone() {
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    throw new MicError('insecure', 'המיקרופון עובד רק בכתובת מאובטחת (https) או ב-localhost.');
  }
  try {
    return await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
    });
  } catch (err) {
    if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
      throw new MicError('denied', 'לא ניתנה הרשאה למיקרופון. אפשר לאשר אותה דרך סמל המנעול שליד כתובת האתר.');
    }
    if (err?.name === 'NotFoundError' || err?.name === 'OverconstrainedError') {
      throw new MicError('nomic', 'לא נמצא מיקרופון במכשיר.');
    }
    throw new MicError('unknown', 'לא הצלחתי לפתוח את המיקרופון.');
  }
}

/**
 * מתחיל הקלטה. מחזיר אובייקט עם:
 *  done   – Promise שמתממש ב-{ wav: Blob|null, heardSpeech: boolean } כשההקלטה נגמרת
 *  stop() – סיום ידני (שומר את מה שהוקלט)
 *  cancel() – ביטול (מוחק את מה שהוקלט)
 */
export async function startRecording({ onLevel, silenceMs = 1700, noSpeechMs = 9000, maxMs = 45000 } = {}) {
  const stream = await openMicrophone();
  const ctx = await getContext();
  const source = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, 'pcm-capture');
  const sink = ctx.createGain();
  sink.gain.value = 0; // לא משמיעים את המיקרופון ברמקול
  source.connect(node);
  node.connect(sink);
  sink.connect(ctx.destination);

  const chunks = [];
  const startedAt = performance.now();
  let noiseFloor = 0.004;
  let calibrated = 0;
  let speechMs = 0;
  let lastVoiceAt = 0;
  let heardSpeech = false;
  let finished = false;
  let resolveDone;
  const done = new Promise((r) => (resolveDone = r));

  const finish = (keep) => {
    if (finished) return;
    finished = true;
    node.port.onmessage = null;
    try {
      source.disconnect();
      node.disconnect();
      sink.disconnect();
    } catch {
      /* already disconnected */
    }
    stream.getTracks().forEach((t) => t.stop());
    onLevel?.(0);
    const wav = keep && heardSpeech && chunks.length ? encodeWav(downsample(concat(chunks), ctx.sampleRate, 16000), 16000) : null;
    resolveDone({ wav, heardSpeech });
  };

  node.port.onmessage = (e) => {
    const chunk = e.data;
    chunks.push(chunk);
    const now = performance.now();
    const elapsed = now - startedAt;
    const chunkMs = (chunk.length / ctx.sampleRate) * 1000;

    let sum = 0;
    for (let i = 0; i < chunk.length; i++) sum += chunk[i] * chunk[i];
    const rms = Math.sqrt(sum / chunk.length);
    onLevel?.(Math.min(1, rms * 12));

    // כיול רעש רקע ב-400 המילישניות הראשונות
    if (elapsed < 400) {
      noiseFloor = (noiseFloor * calibrated + rms) / (calibrated + 1);
      calibrated += 1;
      return;
    }
    const threshold = Math.max(0.012, noiseFloor * 3);
    if (rms > threshold) {
      speechMs += chunkMs;
      lastVoiceAt = now;
      if (speechMs > 250) heardSpeech = true;
    }

    if (heardSpeech && now - lastVoiceAt > silenceMs) finish(true);
    else if (!heardSpeech && elapsed > noSpeechMs) finish(false);
    else if (elapsed > maxMs) finish(true);
  };

  return {
    done,
    stop: () => {
      // לחיצה ידנית על "סיום": שומרים גם דיבור קצר מאוד
      if (speechMs > 0) heardSpeech = true;
      finish(true);
    },
    cancel: () => finish(false)
  };
}

function concat(chunks) {
  const len = chunks.reduce((n, c) => n + c.length, 0);
  const out = new Float32Array(len);
  let o = 0;
  for (const c of chunks) {
    out.set(c, o);
    o += c.length;
  }
  return out;
}

function downsample(input, fromRate, toRate) {
  if (fromRate === toRate) return input;
  const ratio = fromRate / toRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

export function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buffer);
  const writeStr = (off, s) => {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i));
  };
  writeStr(0, 'RIFF');
  v.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); // PCM
  v.setUint16(22, 1, true); // mono
  v.setUint32(24, sampleRate, true);
  v.setUint32(28, sampleRate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  writeStr(36, 'data');
  v.setUint32(40, samples.length * 2, true);
  let o = 44;
  for (let i = 0; i < samples.length; i++, o += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: 'audio/wav' });
}
