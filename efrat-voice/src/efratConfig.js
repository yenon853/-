import { Camera, MessageCircle, Heart, Hand } from 'lucide-react';

export const EFRAT_STAGES = [
  {
    id: 0,
    letter: 'א',
    title: 'אירוע',
    question: 'מה קרה?',
    subtitle: 'מה מצלמה הייתה רואה ושומעת?',
    bgLight: 'bg-sky-50',
    bgCard: 'bg-sky-100/80',
    border: 'border-sky-300',
    ring: 'ring-sky-400/30',
    textMain: 'text-sky-900',
    textAccent: 'text-sky-700',
    badgeBg: 'bg-sky-500',
    aura: 'bg-sky-300',
    icon: Camera,
    helperTip: 'נסו לתאר רק את העובדות שקרו באמת – כמו סרטון במצלמה, בלי לנחש מה הצד השני חשב.'
  },
  {
    id: 1,
    letter: 'פ',
    title: 'פרשנות',
    question: 'מה חשבתי על זה?',
    subtitle: 'איזה סיפור סיפרתי לעצמי בראש?',
    bgLight: 'bg-purple-50',
    bgCard: 'bg-purple-100/80',
    border: 'border-purple-300',
    ring: 'ring-purple-400/30',
    textMain: 'text-purple-900',
    textAccent: 'text-purple-700',
    badgeBg: 'bg-purple-500',
    aura: 'bg-purple-300',
    icon: MessageCircle,
    helperTip: 'לכל אירוע יש כמה פרשנויות! מה חשבתם באותו רגע? והאם יכול להיות הסבר נוסף למה שקרה?'
  },
  {
    id: 2,
    letter: 'ר',
    title: 'רגש',
    question: 'מה הרגשתי?',
    subtitle: 'איזה רגש התעורר אצלי בגוף ובלב?',
    bgLight: 'bg-rose-50',
    bgCard: 'bg-rose-100/80',
    border: 'border-rose-300',
    ring: 'ring-rose-400/30',
    textMain: 'text-rose-900',
    textAccent: 'text-rose-700',
    badgeBg: 'bg-rose-500',
    aura: 'bg-rose-300',
    icon: Heart,
    helperTip: 'כל רגש הוא לגיטימי ומותר להרגיש אותו. כשאנחנו נותנים שם לרגש, כבר קל יותר להירגע.'
  },
  {
    id: 3,
    letter: 'ת',
    title: 'תגובה',
    question: 'איך אבחר להגיב?',
    subtitle: 'עוצרים רגע ובוחרים תגובה מקדמת',
    bgLight: 'bg-emerald-50',
    bgCard: 'bg-emerald-100/80',
    border: 'border-emerald-300',
    ring: 'ring-emerald-400/30',
    textMain: 'text-emerald-900',
    textAccent: 'text-emerald-700',
    badgeBg: 'bg-emerald-600',
    aura: 'bg-emerald-300',
    icon: Hand,
    helperTip: 'אחרי שהפרדנו בין האירוע לפרשנות וזיהינו את הרגש – אילו דרכי תגובה יש לנו שיעשו לנו טוב?'
  }
];

// keywords: מילים שמזהות את הרגש גם כשהילד אומר אותו בקול ("הייתי עצוב", "נעלבתי")
export const EMOTION_OPTIONS = [
  { id: 'hurt', label: 'עלבון / פגיעה', emoji: '🥺', keywords: ['עלבון', 'נעלב', 'פגיעה', 'נפגע', 'פגוע'] },
  { id: 'angry', label: 'כעס', emoji: '😠', keywords: ['כעס', 'כועס', 'עצבני', 'עצבנית', 'התעצבנ'] },
  { id: 'sad', label: 'עצב', emoji: '😢', keywords: ['עצב', 'עצוב', 'בכיתי', 'בוכה'] },
  { id: 'frustrated', label: 'תסכול', emoji: '😤', keywords: ['תסכול', 'מתוסכל'] },
  { id: 'disappointed', label: 'אכזבה', emoji: '😞', keywords: ['אכזב', 'מאוכזב'] },
  { id: 'confused', label: 'בלבול', emoji: '😕', keywords: ['בלבול', 'מבולבל'] },
  { id: 'lonely', label: 'בדידות', emoji: '😔', keywords: ['בדידות', 'בודד', 'לבד'] },
  { id: 'embarrassed', label: 'מבוכה', emoji: '😳', keywords: ['מבוכה', 'נבוך', 'נבוכה', 'בושה', 'התביישתי', 'מתבייש'] },
  { id: 'scared', label: 'פחד', emoji: '😨', keywords: ['פחד', 'מפחד', 'פחדתי', 'נבהלתי', 'לחץ', 'לחוץ'] },
  { id: 'calm', label: 'הקלה / רוגע', emoji: '😌', keywords: ['הקלה', 'רוגע', 'רגוע', 'נרגעתי'] }
];

export function detectEmotions(text = '') {
  const t = String(text);
  return EMOTION_OPTIONS.filter((em) => em.keywords.some((k) => t.includes(k)));
}

export const QUICK_SCENARIOS = [
  { title: 'לא שיתפו אותי במשחק בהפסקה', text: 'בהפסקה יצאתי לחצר וראיתי שהחברים שלי משחקים כדורגל ולא קראו לי להצטרף.' },
  { title: 'מישהו צחק כשטעיתי בכיתה', text: 'עניתי תשובה לא נכונה בשיעור וילד שישב לידי צחק בקול.' },
  { title: 'חבר לקח לי חפץ בלי רשות', text: 'חבר לקח את הטוש המיוחד שלי מהקלמר בלי לשאול אותי.' },
  { title: 'התנגשות במסדרון', text: 'ילד מהכיתה המקבילה רץ במסדרון, נתקל בי והפיל לי את המחברת על הרצפה.' }
];

export const CHARACTERS = {
  efrat: { name: 'אפרת', short: 'א', listening: 'מקשיבה לך...', thinking: 'חושבת על מה שאמרת...' },
  grandpa: { name: 'סבא חכם', short: 'ס', listening: 'מקשיב לך...', thinking: 'חושב בסבלנות...' }
};

export const GENDER_OPTIONS = [
  { id: 'neutral', label: 'לא משנה' },
  { id: 'boy', label: 'ילד' },
  { id: 'girl', label: 'ילדה' }
];

const g = (gender, boy, girl, neutral) => (gender === 'boy' ? boy : gender === 'girl' ? girl : neutral);

export function greeting(character, gender) {
  if (character === 'grandpa') {
    return `${g(gender, 'שלום חמוד', 'שלום חמודה', 'שלום לך')}, כאן סבא חכם 🤍 יש לי את כל הזמן שבעולם להקשיב. נתחיל בשלב א׳ – אירוע, כמו מצלמה: ${g(
      gender,
      'ספר לי בנחת',
      'ספרי לי בנחת',
      'אפשר לספר לי בנחת'
    )}, מה קרה היום?`;
  }
  return `שלום! נעים להכיר, אני אפרת מכנפי אבירים 💙 איזה יופי שעצרת רגע להתבונן במה שקרה. נתחיל בשלב א׳ – אירוע, כמו מצלמה: ${g(
    gender,
    'ספר לי',
    'ספרי לי',
    'אפשר לספר לי'
  )} במילים שלך, מה קרה?`;
}

export const WELCOME_SUGGESTIONS = ['חברים שיחקו בהפסקה ולא קראו לי', 'מישהו צחק כשטעיתי בכיתה', 'רבתי עם חבר על תור במשחק'];

export const EMPTY_REFLECTION = {
  eventFact: '',
  initialInterpretation: '',
  alternativeInterpretation: '',
  emotions: [],
  emotionIntensity: 3,
  chosenResponse: ''
};

export const SUMMARY_TRIGGER = 'כן, בוא נראה את כרטיסיית האפר"ת שלי!';
