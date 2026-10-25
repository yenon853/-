// הכנת טקסט עברי להקראה: מסירים אימוג'י, לוכסנים של מגדר וקיצורים שמנוע הקול מבטא לא נכון.
const EMOJI_RE = /[\p{Extended_Pictographic}\u{FE0F}\u{200D}\u{20E3}]/gu;
const HEB = '֐-׿';

export function textForSpeech(text = '') {
  return String(text)
    .replace(EMOJI_RE, '')
    // "חמוד/ה" , "ספר/י" → נשארת רק המילה הראשונה כדי שלא יוקרא "לוכסן"
    .replace(new RegExp(`([${HEB}]+)\\/[${HEB}]{1,3}(?![${HEB}])`, 'g'), '$1')
    .replace(/אפר["״]ת/g, 'אפרת')
    .replace(/בי["״]ס/g, 'בית ספר')
    .replace(/([א-ת])[׳']\s?–/g, '$1, ')
    .replace(/[–—]/g, ', ')
    .replace(/[*_#`]/g, '')
    .replace(/\s+([):,.!?])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim();
}
