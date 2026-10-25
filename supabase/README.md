# חיבור טופס "קביעת שיחה" ל-Supabase ולמייל

הטופס באתר שולח כל פנייה לשני מקומות במקביל:

1. **Netlify Forms** — לשליחת מייל אליך על כל פנייה.
2. **Supabase** — לשמירה מסודרת של כל הפניות בטבלה.

אם שניהם נכשלים, הטופס פותח וואטסאפ עם הפרטים, כך שאף פנייה לא הולכת לאיבוד.

## שלב 1: Supabase (פעם אחת, כ-5 דקות)

1. נכנסים ל-supabase.com ופותחים פרויקט חדש (החינמי מספיק).
2. SQL Editor > New query > מדביקים את כל התוכן של `leads.sql` > Run.
3. Project Settings > API, ומעתיקים שני ערכים:
   - **Project URL** (נראה כמו `https://xxxx.supabase.co`)
   - **anon public key** (מפתח ארוך שמתחיל ב-`eyJ`)
4. שולחים לי את שני הערכים, ואני מכניס אותם לאתר.

המפתח הציבורי (anon) מיועד להיות בדפדפן. הוא מאפשר רק להוסיף פנייה, ולא לקרוא את הפניות. **לא לשלוח את ה-service_role key.**

הפניות יופיעו ב-Table Editor > leads.

## שלב 2: מייל על כל פנייה (Netlify)

1. ב-Netlify: Site configuration > Forms > **Enable form detection**.
2. לגרור את קובץ ה-ZIP החדש של האתר.
3. Site configuration > Notifications > Emails and webhooks > **Form submission notifications** > Add notification > Email > yenon853@gmail.com > טופס `contact`.
