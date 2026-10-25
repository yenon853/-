import { buildSystemPrompt, buildUserPrompt, RESPONSE_SCHEMA } from './prompt.js';
import { textForSpeech } from '../shared/speech.js';

const env = process.env;

export const config = {
  geminiKey: env.GEMINI_API_KEY || '',
  geminiModel: env.GEMINI_MODEL || 'gemini-3-flash-preview',
  azureKey: env.AZURE_SPEECH_KEY || '',
  azureRegion: env.AZURE_SPEECH_REGION || 'westeurope',
  voices: {
    efrat: {
      name: env.AZURE_VOICE_EFRAT || 'he-IL-HilaNeural',
      rate: '+0%',
      pitch: '+6%'
    },
    grandpa: {
      name: env.AZURE_VOICE_GRANDPA || 'he-IL-AvriNeural',
      rate: '-10%',
      pitch: '-6%'
    }
  }
};

export class ProviderError extends Error {
  constructor(message, status = 502) {
    super(message);
    this.status = status;
  }
}

// ---------- Gemini: מוח השיחה ----------
export async function generateReply({ message, stage, character, childGender, reflection, history }) {
  if (!config.geminiKey) throw new ProviderError('GEMINI_API_KEY חסר', 503);

  const characterName = character === 'grandpa' ? 'סבא חכם' : 'אפרת';
  const payload = {
    systemInstruction: { parts: [{ text: buildSystemPrompt({ character, childGender, stage, reflection }) }] },
    contents: [{ role: 'user', parts: [{ text: buildUserPrompt({ history, message, characterName }) }] }],
    generationConfig: {
      responseMimeType: 'application/json',
      responseSchema: RESPONSE_SCHEMA
    }
  };

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(config.geminiModel)}:generateContent`;
  let lastErr;
  let delay = 800;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': config.geminiKey },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(25000)
      });
      if (!res.ok) {
        const body = await res.text();
        // שגיאות 4xx (מפתח שגוי, מודל לא קיים) לא ישתפרו בניסיון חוזר
        if (res.status < 500 && res.status !== 429) {
          throw Object.assign(new ProviderError(`Gemini ${res.status}: ${body.slice(0, 300)}`), { fatal: true });
        }
        throw new ProviderError(`Gemini ${res.status}`);
      }
      const data = await res.json();
      const raw = data?.candidates?.[0]?.content?.parts?.map((p) => p.text || '').join('');
      if (!raw) throw new ProviderError('Gemini החזיר תשובה ריקה');
      return JSON.parse(raw);
    } catch (err) {
      lastErr = err;
      if (err.fatal || attempt === 2) break;
      await new Promise((r) => setTimeout(r, delay));
      delay *= 2;
    }
  }
  throw lastErr;
}

// ---------- Azure: הקראה בעברית (TTS) ----------
const escapeXml = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');

export async function synthesizeSpeech({ text, character }) {
  if (!config.azureKey) throw new ProviderError('AZURE_SPEECH_KEY חסר', 503);
  const voice = config.voices[character] || config.voices.efrat;
  const clean = textForSpeech(text);
  if (!clean) throw new ProviderError('אין טקסט להקראה', 400);

  const ssml =
    `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="he-IL">` +
    `<voice name="${voice.name}"><prosody rate="${voice.rate}" pitch="${voice.pitch}">` +
    `${escapeXml(clean)}</prosody></voice></speak>`;

  const res = await fetch(`https://${config.azureRegion}.tts.speech.microsoft.com/cognitiveservices/v1`, {
    method: 'POST',
    headers: {
      'Ocp-Apim-Subscription-Key': config.azureKey,
      'Content-Type': 'application/ssml+xml',
      'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3',
      'User-Agent': 'efrat-voice'
    },
    body: ssml,
    signal: AbortSignal.timeout(20000)
  });
  if (!res.ok) throw new ProviderError(`Azure TTS ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return Buffer.from(await res.arrayBuffer());
}

// ---------- Azure: זיהוי דיבור בעברית (STT) ----------
// מקבל WAV מונו 16kHz 16bit שהדפדפן מכין, עד כ-60 שניות.
export async function transcribeSpeech(wavBuffer) {
  if (!config.azureKey) throw new ProviderError('AZURE_SPEECH_KEY חסר', 503);
  const url =
    `https://${config.azureRegion}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1` +
    `?language=he-IL&format=simple&profanity=masked`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Ocp-Apim-Subscription-Key': config.azureKey,
      'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
      Accept: 'application/json'
    },
    body: wavBuffer,
    signal: AbortSignal.timeout(30000)
  });
  if (!res.ok) throw new ProviderError(`Azure STT ${res.status}: ${(await res.text()).slice(0, 200)}`);
  const data = await res.json();
  if (data.RecognitionStatus === 'Success') return (data.DisplayText || '').trim();
  // NoMatch / InitialSilenceTimeout / BabbleTimeout – לא נשמע דיבור ברור
  return '';
}
