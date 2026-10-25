import express from 'express';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { config, generateReply, synthesizeSpeech, transcribeSpeech } from './providers.js';
import { containsSafetyRisk } from '../shared/safety.js';

const app = express();
app.disable('x-powered-by');
app.set('trust proxy', 1);

// ---------- הגבלת קצב פשוטה לכל כתובת IP ----------
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 90;
const hits = new Map();
function rateLimit(req, res, next) {
  const now = Date.now();
  const key = req.ip;
  const entry = hits.get(key);
  if (!entry || now - entry.start > WINDOW_MS) {
    hits.set(key, { start: now, count: 1 });
    return next();
  }
  entry.count += 1;
  if (entry.count > MAX_PER_WINDOW) return res.status(429).json({ error: 'יותר מדי בקשות, נסו שוב בעוד דקה' });
  next();
}
setInterval(() => {
  const now = Date.now();
  for (const [k, v] of hits) if (now - v.start > WINDOW_MS) hits.delete(k);
}, WINDOW_MS).unref();

app.use('/api', rateLimit);

const str = (v, max) => (typeof v === 'string' ? v.slice(0, max) : '');
const oneOf = (v, list, dflt) => (list.includes(v) ? v : dflt);

// ---------- מצב המערכת: מה מחובר ----------
app.get('/api/health', (_req, res) => {
  res.json({
    llm: Boolean(config.geminiKey),
    voice: Boolean(config.azureKey),
    voices: { efrat: config.voices.efrat.name, grandpa: config.voices.grandpa.name }
  });
});

// ---------- שיחה ----------
app.post('/api/chat', express.json({ limit: '64kb' }), async (req, res) => {
  const b = req.body || {};
  const message = str(b.message, 1000).trim();
  if (!message) return res.status(400).json({ error: 'הודעה ריקה' });

  const stageNum = Number.isInteger(b.stage) && b.stage >= 0 && b.stage <= 3 ? b.stage : 0;
  const r = b.reflection || {};
  const reflection = {
    eventFact: str(r.eventFact, 500),
    initialInterpretation: str(r.initialInterpretation, 500),
    alternativeInterpretation: str(r.alternativeInterpretation, 500),
    emotions: Array.isArray(r.emotions) ? r.emotions.slice(0, 10).map((e) => str(e, 40)) : [],
    chosenResponse: str(r.chosenResponse, 500)
  };
  const history = Array.isArray(b.history)
    ? b.history.slice(-8).map((m) => ({ sender: m?.sender === 'bot' ? 'bot' : 'user', text: str(m?.text, 1000) }))
    : [];

  const keywordRisk = containsSafetyRisk(message);
  try {
    const out = await generateReply({
      message,
      stage: stageNum,
      character: oneOf(b.character, ['efrat', 'grandpa'], 'efrat'),
      childGender: oneOf(b.childGender, ['boy', 'girl', 'neutral'], 'neutral'),
      reflection,
      history
    });
    res.json({
      reply: str(out.reply, 1200),
      recommendedNextStage: Number.isInteger(out.recommendedNextStage) ? out.recommendedNextStage : stageNum,
      extractedEventFact: str(out.extractedEventFact, 500),
      extractedInitialInterpretation: str(out.extractedInitialInterpretation, 500),
      extractedAlternativeInterpretation: str(out.extractedAlternativeInterpretation, 500),
      extractedEmotion: str(out.extractedEmotion, 200),
      extractedChosenResponse: str(out.extractedChosenResponse, 500),
      quickReplies: Array.isArray(out.quickReplies) ? out.quickReplies.slice(0, 3).map((q) => str(q, 120)) : [],
      needsAdultHelp: Boolean(out.needsAdultHelp) || keywordRisk
    });
  } catch (err) {
    console.error('[chat]', err.message);
    res.status(err.status || 502).json({ error: 'מוח השיחה לא זמין כרגע', needsAdultHelp: keywordRisk });
  }
});

// ---------- הקראה ----------
app.post('/api/tts', express.json({ limit: '16kb' }), async (req, res) => {
  const text = str(req.body?.text, 1200);
  const character = oneOf(req.body?.character, ['efrat', 'grandpa'], 'efrat');
  try {
    const audio = await synthesizeSpeech({ text, character });
    res.set({ 'Content-Type': 'audio/mpeg', 'Cache-Control': 'no-store' }).send(audio);
  } catch (err) {
    console.error('[tts]', err.message);
    res.status(err.status || 502).json({ error: 'ההקראה לא זמינה כרגע' });
  }
});

// ---------- זיהוי דיבור ----------
// הקלטה של עד כ-60 שניות ב-16kHz מונו ≈ 1.9MB
app.post('/api/stt', express.raw({ type: ['audio/wav', 'audio/x-wav'], limit: '2.5mb' }), async (req, res) => {
  if (!Buffer.isBuffer(req.body) || req.body.length < 1000) {
    return res.status(400).json({ error: 'ההקלטה קצרה מדי' });
  }
  try {
    const text = await transcribeSpeech(req.body);
    res.json({ text });
  } catch (err) {
    console.error('[stt]', err.message);
    res.status(err.status || 502).json({ error: 'זיהוי הדיבור לא זמין כרגע' });
  }
});

// ---------- הגשת האתר הבנוי (אחרי npm run build) ----------
const dist = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../dist');
if (existsSync(dist)) {
  app.use(express.static(dist));
  app.get(/^(?!\/api\/).*/, (_req, res) => res.sendFile(path.join(dist, 'index.html')));
}

const port = Number(process.env.PORT) || 8787;
app.listen(port, () => {
  console.log(`אפרת מאזינה על http://localhost:${port}`);
  console.log(`  מוח שיחה (Gemini): ${config.geminiKey ? 'מחובר' : 'לא מוגדר – יופעלו תשובות גיבוי'}`);
  console.log(`  קול עברי (Azure):  ${config.azureKey ? 'מחובר' : 'לא מוגדר – יופעל קול הדפדפן'}`);
});
