import { useCallback, useEffect, useRef, useState } from 'react';
import { startRecording, encodeWav, MicError } from './pcmRecorder.js';
import { textForSpeech } from '../../shared/speech.js';
import { IS_ARTIFACT } from '../brain.js';

const BROWSER_PROSODY = {
  efrat: { rate: 1.0, pitch: 1.1 },
  grandpa: { rate: 0.9, pitch: 0.85 }
};

function getSpeechRecognition() {
  return typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined;
}

/**
 * מנוע הקול של האפליקציה.
 * עדיפות ראשונה: Azure דרך השרת (קולות עבריים איכותיים, עובד בכל דפדפן).
 * גיבוי: זיהוי והקראה מובנים של הדפדפן, כשיש להם תמיכה בעברית.
 */
export function useVoice() {
  const [health, setHealth] = useState({ checked: false, llm: false, voice: false });
  const [browserHebrewVoice, setBrowserHebrewVoice] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [level, setLevel] = useState(0);
  const [voiceError, setVoiceError] = useState('');

  const audioRef = useRef(null);
  const recRef = useRef(null);
  const recognitionRef = useRef(null);
  const speakTokenRef = useRef(0);
  const speakResolveRef = useRef(null);

  // ---------- בדיקת מה מחובר בשרת ----------
  useEffect(() => {
    if (IS_ARTIFACT) {
      setHealth({ checked: true, llm: false, voice: false });
      return;
    }
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((h) => setHealth({ checked: true, llm: !!h.llm, voice: !!h.voice }))
      .catch(() => setHealth({ checked: true, llm: false, voice: false }));
  }, []);

  // ---------- קול עברי מובנה בדפדפן (גיבוי) ----------
  useEffect(() => {
    if (!('speechSynthesis' in window)) return;
    const pick = () => {
      const voices = window.speechSynthesis.getVoices();
      setBrowserHebrewVoice(voices.find((v) => /^(he|iw)/i.test(v.lang)) || null);
    };
    pick();
    window.speechSynthesis.addEventListener?.('voiceschanged', pick);
    return () => window.speechSynthesis.removeEventListener?.('voiceschanged', pick);
  }, []);

  // ---------- "פתיחת" נגן השמע בלחיצה הראשונה (נדרש ב-iPad ו-iPhone) ----------
  useEffect(() => {
    const audio = new Audio();
    audio.preload = 'auto';
    audioRef.current = audio;
    const unlock = () => {
      const silent = URL.createObjectURL(encodeWav(new Float32Array(800), 16000));
      audio.src = silent;
      audio
        .play()
        .then(() => audio.pause())
        .catch(() => {})
        .finally(() => URL.revokeObjectURL(silent));
      window.removeEventListener('pointerdown', unlock);
    };
    window.addEventListener('pointerdown', unlock);
    return () => window.removeEventListener('pointerdown', unlock);
  }, []);

  // בעמוד claude.ai המיקרופון חסום, לכן אין שם זיהוי דיבור
  const sttEngine = IS_ARTIFACT ? 'none' : health.voice ? 'cloud' : getSpeechRecognition() ? 'browser' : 'none';
  const ttsEngine = health.voice ? 'cloud' : browserHebrewVoice ? 'browser' : 'none';

  // ---------- הקראה ----------
  const stopSpeaking = useCallback(() => {
    speakTokenRef.current += 1;
    const a = audioRef.current;
    if (a) {
      a.pause();
      a.removeAttribute('src');
    }
    window.speechSynthesis?.cancel();
    speakResolveRef.current?.();
    speakResolveRef.current = null;
    setIsSpeaking(false);
  }, []);

  const speakWithBrowser = useCallback(
    (clean, character, token) =>
      new Promise((resolve) => {
        if (!('speechSynthesis' in window) || !clean) return resolve();
        const u = new SpeechSynthesisUtterance(clean);
        u.lang = 'he-IL';
        if (browserHebrewVoice) u.voice = browserHebrewVoice;
        const p = BROWSER_PROSODY[character] || BROWSER_PROSODY.efrat;
        u.rate = p.rate;
        u.pitch = p.pitch;
        u.onstart = () => token === speakTokenRef.current && setIsSpeaking(true);
        u.onend = u.onerror = () => resolve();
        window.speechSynthesis.speak(u);
      }),
    [browserHebrewVoice]
  );

  /** מקריא טקסט בקול הדמות. ה-Promise מתממש כשההקראה נגמרת (או בוטלה). */
  const speak = useCallback(
    async (text, character = 'efrat') => {
      stopSpeaking();
      const token = speakTokenRef.current;
      const clean = textForSpeech(text);
      if (!clean) return;
      setVoiceError('');

      const finished = () => {
        if (token === speakTokenRef.current) setIsSpeaking(false);
      };

      if (health.voice) {
        try {
          setIsSpeaking(true);
          const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: clean, character })
          });
          if (!res.ok) throw new Error('tts');
          const blob = await res.blob();
          if (token !== speakTokenRef.current) return;
          const url = URL.createObjectURL(blob);
          const audio = audioRef.current;
          await new Promise((resolve) => {
            speakResolveRef.current = resolve;
            audio.onended = audio.onerror = () => resolve();
            audio.src = url;
            audio.play().catch(() => {
              setVoiceError('הדפדפן חסם השמעה אוטומטית. לחצו על כפתור הרמקול שליד ההודעה.');
              resolve();
            });
          });
          URL.revokeObjectURL(url);
          finished();
          return;
        } catch {
          if (token !== speakTokenRef.current) return;
          // נפילה לקול הדפדפן
        }
      }

      if (browserHebrewVoice || 'speechSynthesis' in window) {
        if (!browserHebrewVoice) setVoiceError('אין קול עברי מובנה במכשיר הזה, וההקראה עשויה להישמע לא טוב.');
        await speakWithBrowser(clean, character, token);
      }
      finished();
    },
    [health.voice, browserHebrewVoice, speakWithBrowser, stopSpeaking]
  );

  // ---------- זיהוי דיבור ----------
  const listenWithBrowser = useCallback(
    (onInterim) =>
      new Promise((resolve, reject) => {
        const SR = getSpeechRecognition();
        if (!SR) return reject(new MicError('unsupported', 'הדפדפן הזה לא תומך בזיהוי דיבור. נסו Chrome, או הגדירו את Azure בשרת.'));
        const rec = new SR();
        rec.lang = 'he-IL';
        rec.continuous = false;
        rec.interimResults = true;
        let finalText = '';
        let lastText = '';
        rec.onresult = (e) => {
          let interim = '';
          finalText = '';
          for (const r of e.results) {
            if (r.isFinal) finalText += r[0].transcript;
            else interim += r[0].transcript;
          }
          lastText = (finalText + interim).trim();
          onInterim?.(lastText);
        };
        rec.onerror = (e) => {
          if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
            reject(new MicError('denied', 'לא ניתנה הרשאה למיקרופון. אפשר לאשר אותה דרך סמל המנעול שליד כתובת האתר.'));
          } else if (e.error === 'network') {
            reject(new MicError('network', 'זיהוי הדיבור של הדפדפן דורש חיבור לאינטרנט.'));
          }
        };
        rec.onend = () => {
          recognitionRef.current = null;
          resolve((finalText || lastText).trim());
        };
        recognitionRef.current = rec;
        rec.start();
      }),
    []
  );

  /**
   * מאזין לדיבור אחד ומחזיר את הטקסט שזוהה: '' אם לא נשמע דיבור, null אם הייתה שגיאה.
   * ההאזנה נעצרת לבד כשהילד מפסיק לדבר, או ידנית עם stopListening.
   */
  const listen = useCallback(
    async ({ onInterim } = {}) => {
      if (recRef.current || recognitionRef.current) return null;
      stopSpeaking();
      setVoiceError('');
      setIsListening(true);
      try {
        if (health.voice) {
          const rec = await startRecording({ onLevel: setLevel });
          recRef.current = rec;
          const { wav } = await rec.done;
          recRef.current = null;
          setIsListening(false);
          if (!wav) return '';
          setIsTranscribing(true);
          const res = await fetch('/api/stt', { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav });
          if (!res.ok) throw new MicError('stt', 'לא הצלחתי לפענח את ההקלטה. אפשר לנסות שוב או לכתוב.');
          const { text } = await res.json();
          return text || '';
        }
        return await listenWithBrowser(onInterim);
      } catch (err) {
        setVoiceError(err instanceof MicError ? err.message : 'משהו השתבש בהקלטה. אפשר לנסות שוב או לכתוב.');
        return null;
      } finally {
        recRef.current = null;
        setIsListening(false);
        setIsTranscribing(false);
        setLevel(0);
      }
    },
    [health.voice, listenWithBrowser, stopSpeaking]
  );

  const stopListening = useCallback(() => {
    recRef.current?.stop();
    recognitionRef.current?.stop();
  }, []);

  const cancelListening = useCallback(() => {
    recRef.current?.cancel();
    recognitionRef.current?.abort();
  }, []);

  return {
    health,
    sttEngine,
    ttsEngine,
    isListening,
    isTranscribing,
    isSpeaking,
    level,
    voiceError,
    clearVoiceError: () => setVoiceError(''),
    speak,
    stopSpeaking,
    listen,
    stopListening,
    cancelListening
  };
}
