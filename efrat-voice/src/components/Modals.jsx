import { useEffect, useState } from 'react';
import { ShieldAlert, X, Award, Volume2, Download, Trash2, Printer } from 'lucide-react';

function Overlay({ children, onClose, labelledBy }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 print:static print:bg-white"
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledBy}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {children}
    </div>
  );
}

const CloseBtn = ({ onClick }) => (
  <button onClick={onClick} aria-label="סגירה" className="text-slate-400 hover:text-slate-600 p-1 print:hidden">
    <X className="w-5 h-5" />
  </button>
);

// ---------- פנייה למבוגר / התראת מוגנות ----------
export function AdultHelpModal({ isSafetyAlert, onClose }) {
  return (
    <Overlay onClose={onClose} labelledBy="adult-title">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 border-2 border-rose-200 shadow-xl text-right">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-rose-700">
            <ShieldAlert className="w-6 h-6" />
            <h3 id="adult-title" className="text-lg font-extrabold">
              אנחנו כאן איתך! 💙
            </h3>
          </div>
          <CloseBtn onClick={onClose} />
        </div>

        <p className="text-sm text-slate-700 leading-relaxed mb-4">
          {isSafetyAlert
            ? 'שמתי לב שסיפרת על משהו שצריך בשבילו עזרה של מבוגר. כשקורה משהו פוגע או מסוכן, הכי חשוב לא להישאר עם זה לבד. בואו נלך עכשיו למבוגר מהצוות.'
            : 'תמיד מותר ומומלץ לבקש שיחה עם מבוגר מצוות בית הספר "כנפי אבירים". למי תרצה או תרצי לפנות עכשיו?'}
        </p>

        <div className="space-y-2.5 mb-4">
          <div className="p-3 rounded-2xl bg-sky-50 border border-sky-200 flex items-center justify-between">
            <div>
              <div className="font-bold text-sm text-sky-950">המחנך או המחנכת, המורה התורנית</div>
              <div className="text-xs text-slate-600">פנייה מיידית בכיתה או בחצר</div>
            </div>
            <span className="text-lg" aria-hidden>
              👩‍🏫
            </span>
          </div>
          <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-between">
            <div>
              <div className="font-bold text-sm text-amber-950">יועצת בית הספר / שי ושרית</div>
              <div className="text-xs text-slate-600">שיחה אישית ורגועה</div>
            </div>
            <span className="text-lg" aria-hidden>
              💛
            </span>
          </div>
          {isSafetyAlert && (
            <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-950 leading-relaxed">
              <div className="font-bold mb-1">גם מחוץ לבית הספר יש מי שמקשיב:</div>
              <div>מוקד 105 – הגנה על ילדים ובני נוער</div>
              <div>ער״ן – עזרה ראשונה נפשית: 1201</div>
              <div>בסכנה מיידית: משטרה 100</div>
            </div>
          )}
        </div>

        <button onClick={onClose} className="w-full bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl text-sm">
          הבנתי, תודה!
        </button>
      </div>
    </Overlay>
  );
}

// ---------- כרטיסיית הסיכום של הילד ----------
export function SummaryModal({ reflection, characterName, onSpeak, onClose }) {
  const r = reflection;
  const emotionsText = r.emotions.length ? r.emotions.map((e) => `${e.emoji} ${e.label}`).join(', ') : '';
  const spoken = [
    'הנה כרטיסיית האפרת שלך.',
    r.eventFact && `מה קרה: ${r.eventFact}.`,
    r.initialInterpretation && `בהתחלה חשבת: ${r.initialInterpretation}.`,
    r.alternativeInterpretation && `ואז מצאת עוד זווית: ${r.alternativeInterpretation}.`,
    r.emotions.length && `הרגשת: ${r.emotions.map((e) => e.label).join(', ')}.`,
    r.chosenResponse && `ובחרת להגיב כך: ${r.chosenResponse}.`,
    'כל הכבוד!'
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Overlay onClose={onClose} labelledBy="summary-title">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 border-2 border-amber-200 shadow-xl text-right max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Award className="w-6 h-6 text-amber-500" />
            <h3 id="summary-title" className="text-lg font-extrabold text-sky-950">
              כרטיסיית האפר״ת שלי • כנפי אבירים
            </h3>
          </div>
          <CloseBtn onClick={onClose} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          <div className="p-3.5 rounded-2xl bg-sky-50 border-2 border-sky-200">
            <div className="font-black text-sky-900 text-sm mb-1">📷 א – אירוע (מה קרה?)</div>
            <p className="text-xs text-slate-700">{r.eventFact || 'עדיין לא תואר אירוע'}</p>
          </div>
          <div className="p-3.5 rounded-2xl bg-purple-50 border-2 border-purple-200">
            <div className="font-black text-purple-900 text-sm mb-1">💭 פ – פרשנות (מה חשבתי?)</div>
            <p className="text-xs text-slate-700 mb-1">
              <strong>בהתחלה:</strong> {r.initialInterpretation || '—'}
            </p>
            <p className="text-xs text-purple-900 font-bold">
              <strong>זווית נוספת:</strong> {r.alternativeInterpretation || '—'}
            </p>
          </div>
          <div className="p-3.5 rounded-2xl bg-rose-50 border-2 border-rose-200">
            <div className="font-black text-rose-900 text-sm mb-1">❤️ ר – רגש (מה הרגשתי?)</div>
            <p className="text-xs text-slate-700">{emotionsText || 'טרם נבחרו רגשות'}</p>
            {r.emotions.length > 0 && <p className="text-xs text-rose-800 mt-1">עוצמה: {r.emotionIntensity} מתוך 5</p>}
          </div>
          <div className="p-3.5 rounded-2xl bg-emerald-50 border-2 border-emerald-200">
            <div className="font-black text-emerald-900 text-sm mb-1">✋ ת – תגובה (איך אבחר להגיב?)</div>
            <p className="text-xs text-slate-700">{r.chosenResponse || 'טרם נבחרה תגובה'}</p>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-3 text-xs text-amber-950 font-medium mb-4">
          🌟 <strong>כל הכבוד!</strong> גם כש{characterName} לא לידכם בטאבלט, תמיד אפשר לעצור רגע, לשאול מה המצלמה ראתה, לחפש עוד פרשנות ולבחור תגובה חכמה!
        </div>

        <div className="flex flex-wrap justify-end gap-2 print:hidden">
          <button
            onClick={() => onSpeak(spoken)}
            className="bg-white border border-sky-300 text-sky-800 hover:bg-sky-50 font-bold px-4 py-2.5 rounded-xl text-sm flex items-center gap-1.5"
          >
            <Volume2 className="w-4 h-4" />
            הקראת הכרטיסייה
          </button>
          <button
            onClick={() => window.print()}
            className="bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 font-bold px-4 py-2.5 rounded-xl text-sm flex items-center gap-1.5"
          >
            <Printer className="w-4 h-4" />
            הדפסה
          </button>
          <button onClick={onClose} className="bg-sky-600 hover:bg-sky-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm">
            חזרה לשיחה
          </button>
        </div>
      </div>
    </Overlay>
  );
}

// ---------- ממשק צוות ויומן פיילוט ----------
const LOG_KEY = 'efrat-pilot-log-v1';

function readLog() {
  try {
    return JSON.parse(localStorage.getItem(LOG_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeLog(entries) {
  try {
    localStorage.setItem(LOG_KEY, JSON.stringify(entries));
    return true;
  } catch {
    return false;
  }
}

function downloadCsv(entries) {
  const cols = [
    ['date', 'תאריך'],
    ['character', 'דמות'],
    ['childGender', 'פנייה'],
    ['stageReached', 'שלב שהושג'],
    ['voiceTurns', 'תשובות בקול'],
    ['separatedFactFromThought', 'הפריד/ה אירוע מפרשנות'],
    ['foundNewInterpretation', 'הועלו פרשנויות נוספות'],
    ['preferredCharacter', 'העדפת דמות'],
    ['teacherNote', 'הערת צוות']
  ];
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const rows = [cols.map((c) => esc(c[1])).join(',')].concat(
    entries.map((e) => cols.map(([k]) => esc(typeof e[k] === 'boolean' ? (e[k] ? 'כן' : 'לא') : e[k])).join(','))
  );
  const blob = new Blob(['﻿' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `יומן-פיילוט-אפרת-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

export function TeamModal({ sessionInfo, voiceStatus, onClose }) {
  const [form, setForm] = useState({
    separatedFactFromThought: false,
    foundNewInterpretation: false,
    preferredCharacter: 'לבחירת התלמיד/ה',
    teacherNote: ''
  });
  const [log, setLog] = useState(readLog);
  const [banner, setBanner] = useState('');

  const save = () => {
    const entry = { date: new Date().toLocaleString('he-IL'), ...sessionInfo, ...form };
    const next = [...log, entry];
    const ok = writeLog(next);
    setLog(next);
    setBanner(ok ? '✓ התצפית נשמרה ביומן הפיילוט במכשיר הזה.' : 'התצפית נשמרה זמנית בלבד – הדפדפן חוסם שמירה מקומית.');
    setForm((f) => ({ ...f, teacherNote: '' }));
    setTimeout(() => setBanner(''), 3500);
  };

  const clear = () => {
    if (!window.confirm('למחוק את כל התצפיות השמורות במכשיר הזה?')) return;
    writeLog([]);
    setLog([]);
  };

  return (
    <Overlay onClose={onClose} labelledBy="team-title">
      <div className="bg-white rounded-3xl max-w-2xl w-full p-6 border-2 border-slate-200 shadow-xl text-right max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
          <div>
            <h3 id="team-title" className="text-lg font-extrabold text-slate-900">
              ממשק צוות ותצפית התנסות • בי״ס כנפי אבירים
            </h3>
            <p className="text-xs text-slate-500">מובילי היוזמה: שי עובדיה ושרית | ליווי תקשוב: צפנת וינון אהרן זנו</p>
          </div>
          <CloseBtn onClick={onClose} />
        </div>

        <div className="mb-4 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          {voiceStatus.map((s) => (
            <div key={s.label} className={`p-2.5 rounded-xl border ${s.ok ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
              <div className="font-bold text-slate-800">{s.label}</div>
              <div className={s.ok ? 'text-emerald-800' : 'text-amber-900'}>{s.value}</div>
            </div>
          ))}
        </div>

        <div className="mb-4 bg-slate-50 p-4 rounded-2xl border border-slate-200">
          <h4 className="text-xs font-extrabold text-slate-700 mb-2">מדדי הצלחה בתצפית הנוכחית (טופס למידה מהצלחות):</h4>
          <p className="text-xs text-slate-500 mb-2">
            בשיחה הנוכחית: {sessionInfo.character}, הגיע/ה עד שלב {sessionInfo.stageReached}, {sessionInfo.voiceTurns} תשובות בקול.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            <label className="flex items-center gap-2 bg-white p-2.5 rounded-xl border border-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={form.separatedFactFromThought}
                onChange={(e) => setForm({ ...form, separatedFactFromThought: e.target.checked })}
              />
              <span>התלמיד/ה הפריד/ה בין האירוע לפרשנות</span>
            </label>
            <label className="flex items-center gap-2 bg-white p-2.5 rounded-xl border border-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={form.foundNewInterpretation}
                onChange={(e) => setForm({ ...form, foundNewInterpretation: e.target.checked })}
              />
              <span>הועלו פרשנויות ודרכי תגובה נוספות</span>
            </label>
          </div>

          <label className="block text-xs font-bold text-slate-700 mt-3 mb-1">העדפת דמות של התלמיד/ה:</label>
          <select
            value={form.preferredCharacter}
            onChange={(e) => setForm({ ...form, preferredCharacter: e.target.value })}
            className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs"
          >
            <option>לבחירת התלמיד/ה</option>
            <option>אפרת החוקרת</option>
            <option>סבא חכם</option>
            <option>שתי הדמויות באותה מידה</option>
          </select>

          <label className="block text-xs font-bold text-slate-700 mt-3 mb-1">תובנות מהתצפית:</label>
          <textarea
            value={form.teacherNote}
            onChange={(e) => setForm({ ...form, teacherNote: e.target.value })}
            rows={2}
            placeholder="למשל: האם הדיבור בקול עזר לילד להתבטא? (בלי שמות תלמידים)"
            className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs"
          />

          {banner && (
            <div className="mt-2 text-xs text-emerald-700 font-bold bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">{banner}</div>
          )}
        </div>

        <div className="flex flex-wrap justify-between items-center gap-2">
          <div className="flex gap-2">
            <button onClick={save} className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-2 rounded-xl text-xs">
              שמירת תצפית התנסות
            </button>
            <button
              onClick={() => downloadCsv(log)}
              disabled={!log.length}
              className="bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-40 text-slate-800 font-bold px-3 py-2 rounded-xl text-xs flex items-center gap-1"
            >
              <Download className="w-3.5 h-3.5" />
              ייצוא לאקסל ({log.length})
            </button>
            <button
              onClick={clear}
              disabled={!log.length}
              aria-label="מחיקת היומן"
              className="bg-white border border-slate-300 hover:bg-rose-50 disabled:opacity-40 text-rose-700 px-2.5 py-2 rounded-xl text-xs"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
          <button onClick={onClose} className="bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold px-4 py-2 rounded-xl text-xs">
            סגירה
          </button>
        </div>
      </div>
    </Overlay>
  );
}
