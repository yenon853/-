import { useEffect, useRef, useState } from 'react';
import {
  Camera,
  MessageCircle,
  Heart,
  Hand,
  Mic,
  Square,
  Volume2,
  VolumeX,
  Send,
  Sparkles,
  UserCheck,
  RotateCcw,
  CheckCircle2,
  Award,
  ClipboardList,
  Lightbulb,
  Headphones,
  Loader2,
  X
} from 'lucide-react';
import { EfratCharacterSVG, WiseGrandpaSVG } from './characters.jsx';
import {
  EFRAT_STAGES,
  EMOTION_OPTIONS,
  QUICK_SCENARIOS,
  CHARACTERS,
  GENDER_OPTIONS,
  WELCOME_SUGGESTIONS,
  EMPTY_REFLECTION,
  SUMMARY_TRIGGER,
  greeting,
  detectEmotions
} from './efratConfig.js';
import { getFallbackResponse } from './fallback.js';
import { useVoice } from './voice/useVoice.js';
import { containsSafetyRisk } from '../shared/safety.js';
import { IS_ARTIFACT, askClaude } from './brain.js';
import { AdultHelpModal, SummaryModal, TeamModal } from './components/Modals.jsx';

let msgCounter = 0;
const newId = (p) => `${p}-${Date.now()}-${++msgCounter}`;

const welcomeMessage = (character, gender) => ({
  id: newId('welcome'),
  sender: 'bot',
  stage: 0,
  text: greeting(character, gender),
  suggestions: WELCOME_SUGGESTIONS
});

function mergeEmotions(current, found) {
  const ids = new Set(current.map((e) => e.id));
  return [...current, ...found.filter((e) => !ids.has(e.id))];
}

async function requestReply(body) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.reply) {
    const err = new Error('chat unavailable');
    err.needsAdultHelp = Boolean(data.needsAdultHelp);
    throw err;
  }
  return data;
}

export default function App() {
  const [characterType, setCharacterType] = useState('efrat');
  const [childGender, setChildGender] = useState('neutral');
  const character = CHARACTERS[characterType];

  const [activeStage, setActiveStage] = useState(0);
  const [maxStageReached, setMaxStageReached] = useState(0);
  const [reflection, setReflection] = useState(EMPTY_REFLECTION);
  const [messages, setMessages] = useState(() => [welcomeMessage('efrat', 'neutral')]);
  const [inputText, setInputText] = useState('');
  const [interimText, setInterimText] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [voiceChat, setVoiceChat] = useState(false);
  const [voiceTurns, setVoiceTurns] = useState(0);
  const [nothingHeard, setNothingHeard] = useState(false);

  const [safetyAlertOpen, setSafetyAlertOpen] = useState(false);
  const [adultHelpModalOpen, setAdultHelpModalOpen] = useState(false);
  const [teamModalOpen, setTeamModalOpen] = useState(false);
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);

  const voice = useVoice();
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const busyRef = useRef(false);

  // תמונת מצב עדכנית לשימוש בתוך פעולות אסינכרוניות (לולאת הקול)
  const latest = useRef({});
  const anyModalOpen = safetyAlertOpen || adultHelpModalOpen || teamModalOpen || summaryModalOpen;
  latest.current = { messages, activeStage, reflection, characterType, childGender, autoSpeak, voiceChat, anyModalOpen };

  // כשנפתחת התראת מוגנות – עוצרים הקשבה ושיחה קולית, ומפנים את הילד למבוגר
  useEffect(() => {
    if (safetyAlertOpen) {
      voice.cancelListening();
      setVoiceChat(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [safetyAlertOpen]);

  // גוללים רק את אזור השיחה, לא את כל הדף (חשוב בטלפון ובטאבלט)
  useEffect(() => {
    const el = chatEndRef.current?.parentElement;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages, isThinking]);

  // ---------- תור קולי: הקשבה → שליחה ----------
  const sendRef = useRef(null);

  const listenTurn = async ({ autoSend }) => {
    setNothingHeard(false);
    setInterimText('');
    const text = await voice.listen({ onInterim: setInterimText });
    setInterimText('');
    if (text === null) return; // שגיאה – ההודעה כבר מוצגת
    if (!text) {
      setNothingHeard(true);
      return;
    }
    setVoiceTurns((n) => n + 1);
    if (autoSend) {
      sendRef.current(text);
    } else {
      setInputText((prev) => (prev ? `${prev} ${text}` : text));
      inputRef.current?.focus();
    }
  };

  const speakAndMaybeListen = async (text, { listenAfter }) => {
    await voice.speak(text, latest.current.characterType);
    if (listenAfter && latest.current.voiceChat && !latest.current.anyModalOpen && !busyRef.current) {
      listenTurn({ autoSend: true });
    }
  };

  // ---------- שליחת הודעה ----------
  const handleSendMessage = async (customText) => {
    const textToSend = (customText !== undefined ? customText : inputText).trim();
    if (!textToSend || busyRef.current) return;

    if (textToSend === SUMMARY_TRIGGER) {
      setSummaryModalOpen(true);
      return;
    }

    const { messages: history, activeStage: stage, reflection: refl, characterType: charType, childGender: gender } = latest.current;

    const keywordRisk = containsSafetyRisk(textToSend);
    if (keywordRisk) {
      setSafetyAlertOpen(true);
      setVoiceChat(false);
    }

    busyRef.current = true;
    voice.stopSpeaking();
    setMessages((prev) => [...prev, { id: newId('user'), sender: 'user', stage, text: textToSend }]);
    setInputText('');
    setNothingHeard(false);
    setIsThinking(true);

    let ai;
    let serverRisk = false;
    const chatBody = {
      message: textToSend,
      stage,
      character: charType,
      childGender: gender,
      reflection: { ...refl, emotions: refl.emotions.map((e) => e.label) },
      history: history.slice(-8).map((m) => ({ sender: m.sender, text: m.text }))
    };
    try {
      if (voice.health.llm) ai = await requestReply(chatBody);
      else if (IS_ARTIFACT) ai = await askClaude(chatBody);
      else throw new Error('llm off');
    } catch (err) {
      serverRisk = Boolean(err.needsAdultHelp);
      ai = getFallbackResponse(textToSend, stage, refl, gender);
    }
    setIsThinking(false);
    busyRef.current = false;

    // עדכון הכרטיסייה ממה שזוהה בשיחה
    const foundEmotions = detectEmotions(`${ai.extractedEmotion || ''} ${stage === 2 ? textToSend : ''}`);
    setReflection((prev) => ({
      ...prev,
      eventFact: ai.extractedEventFact || prev.eventFact || (stage === 0 ? textToSend : ''),
      initialInterpretation:
        ai.extractedInitialInterpretation || prev.initialInterpretation || (stage === 1 ? textToSend : ''),
      alternativeInterpretation:
        ai.extractedAlternativeInterpretation ||
        prev.alternativeInterpretation ||
        (stage === 1 && prev.initialInterpretation ? textToSend : ''),
      emotions: mergeEmotions(prev.emotions, foundEmotions),
      chosenResponse: ai.extractedChosenResponse || prev.chosenResponse || (stage === 3 ? textToSend : '')
    }));

    const needsAdult = Boolean(ai.needsAdultHelp) || keywordRisk || serverRisk;
    if (needsAdult) {
      setSafetyAlertOpen(true);
      setVoiceChat(false);
    }

    // מתקדמים לכל היותר שלב אחד קדימה בכל תור
    const rec = Number.isInteger(ai.recommendedNextStage) ? ai.recommendedNextStage : stage;
    const nextStage = Math.max(0, Math.min(3, Math.min(rec, stage + 1)));
    setActiveStage(nextStage);
    setMaxStageReached((m) => Math.max(m, nextStage));

    setMessages((prev) => [
      ...prev,
      { id: newId('bot'), sender: 'bot', stage: nextStage, text: ai.reply, suggestions: ai.quickReplies || [] }
    ]);

    const { autoSpeak: shouldSpeak, voiceChat: inVoiceChat } = latest.current;
    if (shouldSpeak || inVoiceChat) {
      speakAndMaybeListen(ai.reply, { listenAfter: inVoiceChat && !needsAdult });
    }
  };
  sendRef.current = handleSendMessage;

  // ---------- כפתורים ----------
  const handleMicButton = () => {
    voice.clearVoiceError();
    if (voice.isListening) {
      voice.stopListening();
      return;
    }
    if (voice.isTranscribing || isThinking) return;
    listenTurn({ autoSend: voiceChat });
  };

  const toggleVoiceChat = () => {
    if (voiceChat) {
      setVoiceChat(false);
      voice.cancelListening();
      voice.stopSpeaking();
      return;
    }
    setVoiceChat(true);
    latest.current.voiceChat = true;
    const lastBot = [...messages].reverse().find((m) => m.sender === 'bot');
    if (lastBot) speakAndMaybeListen(lastBot.text, { listenAfter: true });
    else listenTurn({ autoSend: true });
  };

  const resetIfFresh = (charType, gender) => {
    if (messages.length === 1) setMessages([welcomeMessage(charType, gender)]);
  };

  const handleSwitchCharacter = (newChar) => {
    setCharacterType(newChar);
    resetIfFresh(newChar, childGender);
  };

  const handleSwitchGender = (g) => {
    setChildGender(g);
    resetIfFresh(characterType, g);
  };

  const handleResetSession = () => {
    voice.stopSpeaking();
    voice.cancelListening();
    setVoiceChat(false);
    setActiveStage(0);
    setMaxStageReached(0);
    setReflection(EMPTY_REFLECTION);
    setInputText('');
    setVoiceTurns(0);
    setNothingHeard(false);
    setMessages([welcomeMessage(characterType, childGender)]);
  };

  const toggleEmotionChip = (em) => {
    setReflection((prev) => {
      const exists = prev.emotions.some((e) => e.id === em.id);
      return { ...prev, emotions: exists ? prev.emotions.filter((e) => e.id !== em.id) : [...prev.emotions, em] };
    });
    if (!inputText.includes(em.label)) {
      setInputText((prev) => (prev ? `${prev}, ${em.label}` : `הרגשתי ${em.label}`));
    }
  };

  const closeHelp = () => {
    setAdultHelpModalOpen(false);
    setSafetyAlertOpen(false);
  };

  const currentStage = EFRAT_STAGES[activeStage];
  const characterStatus = voice.isListening ? 'listening' : isThinking || voice.isTranscribing ? 'thinking' : null;
  const characterStatusText = voice.isListening ? character.listening : character.thinking;
  const CharacterSVG = characterType === 'efrat' ? EfratCharacterSVG : WiseGrandpaSVG;

  const voiceLabel = IS_ARTIFACT
    ? 'Claude עונה, הקראה בקול'
    : !voice.health.checked
    ? 'בודק חיבור...'
    : voice.health.voice
    ? 'קול עברי מחובר'
    : voice.sttEngine === 'browser' || voice.ttsEngine === 'browser'
    ? 'קול הדפדפן'
    : 'ללא קול';

  const voiceStatus = [
    {
      label: 'מוח השיחה',
      ok: voice.health.llm || IS_ARTIFACT,
      value: voice.health.llm ? 'Gemini מחובר' : IS_ARTIFACT ? 'Claude (באישור הצופה)' : 'תשובות גיבוי (אין מפתח או אין רשת)'
    },
    {
      label: 'זיהוי דיבור',
      ok: voice.sttEngine !== 'none',
      value: voice.sttEngine === 'cloud' ? 'Azure, עברית' : voice.sttEngine === 'browser' ? 'מובנה בדפדפן' : 'לא זמין במכשיר'
    },
    {
      label: 'הקראה',
      ok: voice.ttsEngine !== 'none',
      value: voice.ttsEngine === 'cloud' ? 'Azure: הילה ואברי' : voice.ttsEngine === 'browser' ? 'קול עברי של המכשיר' : 'אין קול עברי במכשיר'
    }
  ];

  const micBusy = voice.isTranscribing || isThinking;

  return (
    <div dir="rtl" className="min-h-screen bg-gradient-to-b from-amber-50/70 via-sky-50/50 to-white text-slate-800 font-sans flex flex-col">
      {/* ===== כותרת ===== */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-sky-100 shadow-sm px-4 sm:px-6 py-2.5 print:hidden">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center text-white font-black text-xl shadow-sm">
              א
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-extrabold text-sky-950 tracking-tight">תשאלו את אפרת!</h1>
                <span className="hidden md:inline-block bg-amber-100 text-amber-900 text-xs font-bold px-2.5 py-0.5 rounded-full border border-amber-300">
                  בי״ס כנפי אבירים
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">עוצרים רגע ובוחרים תגובה • תרגול מודל אפר״ת</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="bg-slate-100 p-1 rounded-xl flex items-center border border-slate-200 text-xs font-bold" role="group" aria-label="בחירת דמות">
              {[
                ['efrat', '🔍', 'אפרת', 'text-sky-700'],
                ['grandpa', '👴🏼', 'סבא חכם', 'text-teal-800']
              ].map(([id, icon, label, tone]) => (
                <button
                  key={id}
                  onClick={() => handleSwitchCharacter(id)}
                  aria-pressed={characterType === id}
                  className={`px-2.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                    characterType === id ? `bg-white ${tone} shadow-sm` : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <span aria-hidden>{icon}</span>
                  <span>{label}</span>
                </button>
              ))}
            </div>

            <label className="text-xs font-bold text-slate-600 flex items-center gap-1 bg-white border border-slate-200 rounded-xl px-2 py-1.5">
              <span>לדבר אליי כ:</span>
              <select value={childGender} onChange={(e) => handleSwitchGender(e.target.value)} className="bg-transparent font-bold text-slate-800 outline-none">
                {GENDER_OPTIONS.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            <button
              onClick={() => {
                const next = !autoSpeak;
                setAutoSpeak(next);
                if (!next) voice.stopSpeaking();
              }}
              title="הקראה אוטומטית של התשובות"
              aria-pressed={autoSpeak}
              className={`p-2 rounded-xl border text-xs font-bold flex items-center gap-1 transition-all ${
                autoSpeak ? 'bg-sky-100 border-sky-300 text-sky-800' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {autoSpeak ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              <span className="hidden sm:inline">{autoSpeak ? 'הקראה פעילה' : 'הקראה כבויה'}</span>
            </button>

            <button
              onClick={() => setAdultHelpModalOpen(true)}
              className="bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-xs"
            >
              <UserCheck className="w-4 h-4 text-rose-600" />
              <span>פנייה למבוגר</span>
            </button>

            <button
              onClick={() => setTeamModalOpen(true)}
              className="bg-slate-800 hover:bg-slate-900 text-white px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-xs"
            >
              <ClipboardList className="w-4 h-4 text-amber-300" />
              <span className="hidden sm:inline">מבט צוות</span>
            </button>
          </div>
        </div>
      </header>

      {/* ===== מדרגות א-פ-ר-ת ===== */}
      <section className="max-w-6xl w-full mx-auto px-4 sm:px-6 pt-3 pb-1 print:hidden">
        <div className="grid grid-cols-4 gap-2 sm:gap-3">
          {EFRAT_STAGES.map((stage) => {
            const StageIcon = stage.icon;
            const isCurrent = activeStage === stage.id;
            const isPassed = maxStageReached > stage.id && !isCurrent;
            return (
              <button
                key={stage.id}
                onClick={() => setActiveStage(stage.id)}
                aria-current={isCurrent ? 'step' : undefined}
                className={`relative text-right p-2.5 sm:p-3.5 rounded-2xl border-2 transition-all flex flex-col justify-between ${
                  isCurrent
                    ? `${stage.bgCard} ${stage.border} ring-4 ${stage.ring} shadow-md scale-[1.02]`
                    : isPassed
                    ? 'bg-white border-emerald-200 opacity-95 hover:opacity-100'
                    : 'bg-white/70 border-slate-200/80 opacity-75 hover:opacity-100'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl ${stage.badgeBg} text-white font-black text-base sm:text-lg flex items-center justify-center shadow-xs`}
                    >
                      {stage.letter}
                    </span>
                    <span className={`font-extrabold text-sm sm:text-base ${stage.textMain}`}>{stage.title}</span>
                  </div>
                  <StageIcon className={`w-4 h-4 sm:w-5 sm:h-5 ${stage.textAccent} shrink-0 hidden sm:block`} />
                </div>
                <p className="text-[11px] sm:text-xs text-slate-600 font-medium leading-tight">{stage.question}</p>
                {isPassed && (
                  <span className="absolute -top-1.5 -left-1.5 bg-emerald-500 text-white rounded-full p-0.5 shadow-xs">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </section>

      <main className="max-w-6xl w-full mx-auto px-4 sm:px-6 py-3 flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 items-start print:hidden">
        {/* ===== עמודת הדמות והכרטיסייה ===== */}
        <div className="lg:col-span-4 flex flex-col gap-3">
          <div className="bg-white rounded-3xl border-2 border-sky-100 shadow-sm p-4 flex flex-col items-center text-center relative overflow-hidden">
            <div className="bg-amber-100/90 border border-amber-300 px-4 py-1 rounded-full mb-1 shadow-2xs">
              <span className="text-xs sm:text-sm font-black text-sky-950">
                {characterType === 'efrat' ? 'נעים להכיר, אפרת! 🔍' : 'נעים להכיר, סבא חכם! 🤍'}
              </span>
            </div>
            <p className="text-xs font-bold text-sky-700 mb-1">עוצרים רגע ובוחרים תגובה</p>

            <button
              type="button"
              onClick={handleMicButton}
              className="rounded-full focus-visible:outline-4 focus-visible:outline-sky-300"
              aria-label={voice.isListening ? 'סיום הקלטה' : `לחצו כדי לדבר עם ${character.name}`}
              title={voice.isListening ? 'סיום הקלטה' : `לחצו כדי לדבר עם ${character.name}`}
            >
              <CharacterSVG activeStage={activeStage} isSpeaking={voice.isSpeaking} status={characterStatus} statusText={characterStatusText} />
            </button>

            <div className={`w-full mt-2 p-3 rounded-2xl border ${currentStage.bgLight} ${currentStage.border} text-right`}>
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-black ${currentStage.textMain}`}>
                  שלב נוכחי: {currentStage.letter} – {currentStage.title} ({currentStage.question})
                </span>
                <Lightbulb className={`w-4 h-4 ${currentStage.textAccent}`} />
              </div>
              <p className="text-xs text-slate-700 leading-relaxed">{currentStage.helperTip}</p>
            </div>
          </div>

          <div className="bg-white rounded-3xl border-2 border-slate-200/80 shadow-sm p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-extrabold text-sm text-slate-800 flex items-center gap-1.5">
                <Award className="w-4 h-4 text-amber-500" />
                <span>כרטיסיית האפר״ת שלי</span>
              </h2>
              <button onClick={() => setSummaryModalOpen(true)} className="text-xs font-bold text-sky-600 hover:text-sky-800 underline">
                הגדלה וסיכום
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-xl bg-sky-50/70 border border-sky-200">
                <div className="font-bold text-sky-900 flex items-center gap-1 mb-0.5">
                  <Camera className="w-3.5 h-3.5 text-sky-600" />
                  <span>א – אירוע (מה המצלמה ראתה?):</span>
                </div>
                <p className="text-slate-700">{reflection.eventFact || <span className="text-slate-400 italic">יתמלא תוך כדי השיחה...</span>}</p>
              </div>

              <div className="p-2.5 rounded-xl bg-purple-50/70 border border-purple-200">
                <div className="font-bold text-purple-900 flex items-center gap-1 mb-0.5">
                  <MessageCircle className="w-3.5 h-3.5 text-purple-600" />
                  <span>פ – פרשנות (מחשבה ראשונה מול חדשה):</span>
                </div>
                {reflection.initialInterpretation ? (
                  <div className="space-y-1">
                    <p className="text-slate-700">
                      <span className="font-semibold">בהתחלה חשבתי:</span> {reflection.initialInterpretation}
                    </p>
                    {reflection.alternativeInterpretation && (
                      <p className="text-purple-800 font-medium bg-white/80 px-2 py-1 rounded-lg border border-purple-200">
                        ✨ <span className="font-bold">פרשנות נוספת:</span> {reflection.alternativeInterpretation}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-slate-400 italic">נגלה יחד בשלב הפרשנות...</p>
                )}
              </div>

              <div className="p-2.5 rounded-xl bg-rose-50/70 border border-rose-200">
                <div className="font-bold text-rose-900 flex items-center gap-1 mb-0.5">
                  <Heart className="w-3.5 h-3.5 text-rose-600" />
                  <span>ר – רגש (מה הרגשתי?):</span>
                </div>
                {reflection.emotions.length > 0 ? (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {reflection.emotions.map((em) => (
                      <span key={em.id} className="bg-white border border-rose-200 px-2 py-0.5 rounded-full text-rose-800 font-bold">
                        {em.emoji} {em.label}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400 italic">נבחר רגשות בשלב הרגש...</p>
                )}
              </div>

              <div className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200">
                <div className="font-bold text-emerald-900 flex items-center gap-1 mb-0.5">
                  <Hand className="w-3.5 h-3.5 text-emerald-600" />
                  <span>ת – תגובה (איך אבחר להגיב?):</span>
                </div>
                <p className="text-slate-700">{reflection.chosenResponse || <span className="text-slate-400 italic">נבחר יחד תגובה מקדמת...</span>}</p>
              </div>
            </div>
          </div>
        </div>

        {/* ===== עמודת השיחה ===== */}
        <div className="lg:col-span-8 bg-white rounded-3xl border-2 border-sky-100 shadow-sm flex flex-col h-[620px] sm:h-[680px] overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-200/80 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${voice.health.voice ? 'bg-emerald-500' : 'bg-amber-400'} animate-pulse`} />
              <span className="font-bold text-sm text-slate-800">שיחה אישית עם {character.name}</span>
              <span className="text-xs text-slate-500 hidden sm:inline">• {voiceLabel}</span>
            </div>

            <div className="flex items-center gap-2">
              {!IS_ARTIFACT && (<button
                onClick={toggleVoiceChat}
                disabled={voice.sttEngine === 'none'}
                aria-pressed={voiceChat}
                title="הדמות מקריאה, מקשיבה ושולחת לבד – בלי להקליד"
                className={`text-xs font-bold px-2.5 py-1 rounded-xl flex items-center gap-1 border shadow-2xs transition-all disabled:opacity-40 ${
                  voiceChat ? 'bg-emerald-600 text-white border-emerald-700' : 'bg-white text-emerald-800 border-emerald-300 hover:bg-emerald-50'
                }`}
              >
                <Headphones className="w-3.5 h-3.5" />
                <span>{voiceChat ? 'שיחה קולית פעילה' : 'שיחה קולית'}</span>
              </button>)}
              <button
                onClick={handleResetSession}
                className="text-xs font-bold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 px-2.5 py-1 rounded-xl flex items-center gap-1 shadow-2xs"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>אירוע חדש</span>
              </button>
            </div>
          </div>

          {messages.length <= 2 && (
            <div className="px-4 py-2.5 bg-sky-50/70 border-b border-sky-100 flex items-center gap-2 overflow-x-auto no-scrollbar">
              <span className="text-xs font-bold text-sky-900 shrink-0">דוגמאות לתרגול מהיר:</span>
              {QUICK_SCENARIOS.map((sc) => (
                <button
                  key={sc.title}
                  onClick={() => handleSendMessage(sc.text)}
                  className="text-xs bg-white hover:bg-sky-100 text-sky-800 border border-sky-200 px-3 py-1 rounded-full font-semibold shrink-0 transition-all shadow-2xs"
                >
                  {sc.title}
                </button>
              ))}
            </div>
          )}

          <div className="flex-1 overflow-y-auto p-4 space-y-4" aria-live="polite">
            {messages.map((msg, idx) => {
              const isBot = msg.sender === 'bot';
              const stageInfo = EFRAT_STAGES[msg.stage ?? 0];
              const isLast = idx === messages.length - 1;
              return (
                <div key={msg.id} className={`flex flex-col ${isBot ? 'items-start' : 'items-end'}`}>
                  <div className="flex items-end gap-2 max-w-[88%] sm:max-w-[80%]">
                    {isBot && (
                      <div
                        className={`w-8 h-8 rounded-2xl ${
                          characterType === 'efrat' ? 'bg-sky-500' : 'bg-teal-600'
                        } text-white flex items-center justify-center font-black text-sm shrink-0 shadow-xs`}
                      >
                        {character.short}
                      </div>
                    )}
                    <div
                      className={`rounded-2xl px-4 py-3 shadow-xs text-sm sm:text-base leading-relaxed ${
                        isBot ? 'bg-slate-100 text-slate-800 rounded-tr-none border border-slate-200/80' : 'bg-sky-600 text-white rounded-tl-none'
                      }`}
                    >
                      {isBot && (
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className={`text-[11px] font-extrabold px-2 py-0.5 rounded-md ${stageInfo.bgCard} ${stageInfo.textMain}`}>
                            שלב {stageInfo.letter}׳ – {stageInfo.title}
                          </span>
                          <button
                            onClick={() => voice.speak(msg.text, characterType)}
                            title="הקראת ההודעה"
                            aria-label="הקראת ההודעה"
                            className="text-slate-400 hover:text-sky-600 p-1 rounded-lg transition-colors"
                          >
                            <Volume2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                      <p className="whitespace-pre-line">{msg.text}</p>
                    </div>
                  </div>

                  {isBot && isLast && msg.suggestions?.length > 0 && !isThinking && (
                    <div className="mt-2.5 mr-10 flex flex-wrap gap-2">
                      {msg.suggestions.map((sug) => (
                        <button
                          key={sug}
                          onClick={() => handleSendMessage(sug)}
                          className="text-xs sm:text-sm bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-300 px-3.5 py-1.5 rounded-2xl font-bold transition-all shadow-2xs flex items-center gap-1.5"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                          <span>{sug}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {(isThinking || voice.isTranscribing) && (
              <div className="flex items-center gap-2 text-slate-500 text-sm px-2">
                <div className="w-8 h-8 rounded-2xl bg-sky-100 text-sky-700 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
                <span className="font-medium animate-pulse">
                  {voice.isTranscribing ? `${character.name} מקשיב${characterType === 'efrat' ? 'ה' : ''} למה שאמרת...` : character.thinking}
                </span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {activeStage === 2 && (
            <div className="px-4 py-2.5 bg-rose-50/90 border-t border-rose-200">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <span className="text-xs font-extrabold text-rose-900">❤️ בחרו את הרגשות שהרגשתם (אפשר יותר מאחד):</span>
                <label className="text-xs font-bold text-rose-700 flex items-center gap-2">
                  <span>עוצמה: {reflection.emotionIntensity}/5</span>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={reflection.emotionIntensity}
                    onChange={(e) => setReflection((p) => ({ ...p, emotionIntensity: Number(e.target.value) }))}
                    className="accent-rose-600 w-24"
                    aria-label="עוצמת הרגש"
                  />
                </label>
              </div>
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
                {EMOTION_OPTIONS.map((em) => {
                  const selected = reflection.emotions.some((e) => e.id === em.id);
                  return (
                    <button
                      key={em.id}
                      onClick={() => toggleEmotionChip(em)}
                      aria-pressed={selected}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 border transition-all flex items-center gap-1 ${
                        selected ? 'bg-rose-600 text-white border-rose-700 shadow-xs scale-105' : 'bg-white text-rose-900 border-rose-200 hover:bg-rose-100'
                      }`}
                    >
                      <span aria-hidden>{em.emoji}</span>
                      <span>{em.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {(voice.voiceError || nothingHeard) && (
            <div className="mx-3 sm:mx-4 mt-2 px-3 py-2 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950 flex items-center justify-between gap-2">
              <span>{voice.voiceError || `לא שמעתי דיבור. לחצו על המיקרופון ודברו בקול ברור, או כתבו ל${character.name}.`}</span>
              <button
                onClick={() => {
                  voice.clearVoiceError();
                  setNothingHeard(false);
                }}
                aria-label="סגירת ההודעה"
                className="text-amber-700 p-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <div className="p-3 sm:p-4 bg-white border-t border-slate-200">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleMicButton}
                disabled={micBusy || voice.sttEngine === 'none'}
                className={`relative px-3.5 py-3 rounded-2xl font-bold text-xs sm:text-sm flex items-center gap-1.5 transition-all shrink-0 shadow-xs disabled:opacity-50 ${
                  voice.isListening ? 'bg-rose-600 text-white' : 'bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200'
                }`}
                title={voice.sttEngine === 'none' ? 'זיהוי דיבור לא זמין במכשיר הזה' : 'דברו בקול'}
              >
                {voice.isListening && (
                  <span
                    aria-hidden
                    className="absolute inset-0 rounded-2xl ring-4 ring-rose-300 transition-transform duration-75"
                    style={{ transform: `scale(${1 + voice.level * 0.25})` }}
                  />
                )}
                {voice.isListening ? (
                  <>
                    <Square className="w-4 h-4 fill-current" />
                    <span>סיימתי</span>
                  </>
                ) : voice.isTranscribing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="hidden sm:inline">מפענח...</span>
                  </>
                ) : (
                  <>
                    <Mic className="w-5 h-5 text-sky-600" />
                    <span className="hidden sm:inline">דברו בקול</span>
                  </>
                )}
              </button>

              <input
                ref={inputRef}
                type="text"
                value={voice.isListening && interimText ? interimText : inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.nativeEvent.isComposing) handleSendMessage();
                }}
                readOnly={voice.isListening}
                maxLength={1000}
                placeholder={voice.isListening ? `${character.name} ${character.listening}` : `כתבו או אמרו בקול תשובה ל${character.name}...`}
                className="flex-1 min-w-0 bg-slate-50 border-2 border-slate-200 focus:border-sky-400 focus:bg-white rounded-2xl px-4 py-3 text-sm sm:text-base outline-none transition-all"
              />

              <button
                type="button"
                onClick={() => handleSendMessage()}
                disabled={!inputText.trim() || isThinking}
                className="bg-sky-600 hover:bg-sky-700 disabled:bg-slate-200 disabled:text-slate-400 text-white px-4 py-3 rounded-2xl font-bold text-sm flex items-center gap-1.5 transition-all shadow-sm shrink-0"
              >
                <span className="hidden sm:inline">שליחה</span>
                <Send className="w-4 h-4 rotate-180" />
              </button>
            </div>
            {IS_ARTIFACT && (
              <p className="mt-2 text-[11px] text-slate-500 font-medium">
                🔊 {character.name} עונה בקול. בגרסה הזו כותבים או בוחרים תשובה. דיבור למיקרופון זמין בגרסת בית הספר המלאה.
              </p>
            )}
            {voiceChat && (
              <p className="mt-2 text-[11px] text-emerald-800 font-medium">
                🎧 שיחה קולית: {character.name} {characterType === 'efrat' ? 'תקריא' : 'יקריא'} כל תשובה ואז {characterType === 'efrat' ? 'תקשיב' : 'יקשיב'} לך. כשמסיימים לדבר, השליחה אוטומטית.
              </p>
            )}
          </div>
        </div>
      </main>

      {(adultHelpModalOpen || safetyAlertOpen) && <AdultHelpModal isSafetyAlert={safetyAlertOpen} onClose={closeHelp} />}

      {summaryModalOpen && (
        <SummaryModal
          reflection={reflection}
          characterName={character.name}
          onSpeak={(t) => voice.speak(t, characterType)}
          onClose={() => {
            voice.stopSpeaking();
            setSummaryModalOpen(false);
          }}
        />
      )}

      {teamModalOpen && (
        <TeamModal
          sessionInfo={{
            character: character.name,
            childGender: GENDER_OPTIONS.find((o) => o.id === childGender)?.label,
            stageReached: `${EFRAT_STAGES[maxStageReached].letter} – ${EFRAT_STAGES[maxStageReached].title}`,
            voiceTurns
          }}
          voiceStatus={voiceStatus}
          onClose={() => setTeamModalOpen(false)}
        />
      )}

    </div>
  );
}
