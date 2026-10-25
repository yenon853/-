// תשובות גיבוי כשמוח השיחה לא זמין (אין אינטרנט או אין מפתח). התרגול ממשיך גם בלי AI.
import { SUMMARY_TRIGGER } from './efratConfig.js';

const g = (gender, boy, girl, neutral) => (gender === 'boy' ? boy : gender === 'girl' ? girl : neutral);

export function getFallbackResponse(userMessage, stage, reflection, gender) {
  const base = {
    extractedEventFact: '',
    extractedInitialInterpretation: '',
    extractedAlternativeInterpretation: '',
    extractedEmotion: '',
    extractedChosenResponse: '',
    needsAdultHelp: false
  };

  if (stage === 0) {
    return {
      ...base,
      reply: `תודה ששיתפת אותי. עכשיו נעבור לשלב פ׳ – פרשנות 💭: מה ${g(gender, 'חשבת', 'חשבת', 'עבר לך')} בראש באותו רגע שזה קרה?`,
      recommendedNextStage: 1,
      extractedEventFact: userMessage,
      quickReplies: ['חשבתי שעושים לי בכוונה', 'חשבתי שלא רוצים להיות חברים שלי', 'חשבתי שזה לא הוגן']
    };
  }

  if (stage === 1 && !reflection.initialInterpretation) {
    return {
      ...base,
      reply: `מובן מאוד שזה מה שעלה לך בראש באותו רגע. ${g(gender, 'בוא', 'בואי', 'בואו')} נסתכל בזכוכית המגדלת 🔍 – איזה הסבר אחר יכול להיות למה שקרה?`,
      recommendedNextStage: 1,
      extractedInitialInterpretation: userMessage,
      quickReplies: ['אולי הם לא שמו לב אליי', 'אולי הוא לא עשה את זה בכוונה', 'אולי היה לו יום קשה']
    };
  }

  if (stage === 1) {
    return {
      ...base,
      reply: `איזו מחשבה חכמה! מצאת עוד דרך להסתכל על מה שקרה. עכשיו שלב ר׳ – רגש ❤️: מה הרגשת בגוף ובלב?`,
      recommendedNextStage: 2,
      extractedAlternativeInterpretation: userMessage,
      quickReplies: ['הרגשתי עלבון וקצת עצב', 'הרגשתי כעס ותסכול', 'כשחשבתי על פרשנות אחרת הרגשתי הקלה']
    };
  }

  if (stage === 2) {
    return {
      ...base,
      reply: `זה טבעי לגמרי להרגיש ככה, וטוב מאוד שנתת שם לרגש. עכשיו שלב ת׳ – תגובה ✋: איך ${g(gender, 'תבחר', 'תבחרי', 'תבחר או תבחרי')} להגיב בפעם הבאה?`,
      recommendedNextStage: 3,
      extractedEmotion: userMessage,
      quickReplies: ['אגש ואבקש להצטרף למשחק בנחת', 'אגיד לחבר ברוגע מה הרגשתי', 'אבקש עזרה מהמורה התורנית']
    };
  }

  return {
    ...base,
    reply: 'איזו בחירה בוגרת וחכמה! 🌟 עברנו יחד את כל ארבעת השלבים של מודל אפר"ת. רוצה לראות את כרטיסיית הסיכום?',
    recommendedNextStage: 3,
    extractedChosenResponse: userMessage,
    quickReplies: [SUMMARY_TRIGGER]
  };
}
