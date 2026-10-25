// מוח השיחה בגרסת claude.ai: כשאין שרת, Claude עונה דרך היכולת "sample" של העמוד.
import { buildSystemPrompt, buildUserPrompt } from '../server/prompt.js';

export const IS_ARTIFACT = import.meta.env.MODE === 'artifact';

let samplePromise = null;
export function getClaudeSample() {
  if (typeof window === 'undefined' || !window.claude?.use) return Promise.resolve(null);
  samplePromise ??= window.claude.use('sample').catch(() => null);
  return samplePromise;
}

const FORMAT = `החזר/י אובייקט JSON אחד בלבד, בלי טקסט לפניו או אחריו, עם השדות:
reply (מחרוזת), recommendedNextStage (מספר 0–3), extractedEventFact, extractedInitialInterpretation,
extractedAlternativeInterpretation, extractedEmotion, extractedChosenResponse (מחרוזות, ריקות אם לא זוהה),
quickReplies (מערך של 2–3 מחרוזות קצרות), needsAdultHelp (true או false).`;

export async function askClaude({ message, stage, character, childGender, reflection, history }) {
  const sample = await getClaudeSample();
  if (!sample) throw new Error('claude unavailable');
  const characterName = character === 'grandpa' ? 'סבא חכם' : 'אפרת';
  const prompt = `${buildSystemPrompt({ character, childGender, stage, reflection })}

${buildUserPrompt({ history, message, characterName })}

${FORMAT}`;
  const out = await sample.json(prompt, { modelTier: 'quick', cache: false });
  if (!out || typeof out.reply !== 'string' || !out.reply.trim()) throw new Error('bad answer');
  return out;
}
