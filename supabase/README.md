# טופס "קביעת שיחה": מייל + Supabase

הטופס באתר שולח כל פנייה לשני מקומות במקביל:

1. **Netlify Forms**, לשליחת מייל אליך על כל פנייה.
2. **Supabase**, לשמירה מסודרת של כל הפניות בטבלה.

אם שניהם נכשלים, הטופס פותח וואטסאפ עם הפרטים, כך שאף פנייה לא הולכת לאיבוד.

## Supabase: כבר מחובר

- פרויקט: **yinonz-bina-site** (אזור eu-central-1), בחשבון yenon853.
- טבלה: `public.leads`, נוצרה מהקובץ `leads.sql`.
- אבטחה: האתר יכול רק להוסיף פנייה. קריאה, שינוי ומחיקה רק לך, מתוך לוח הבקרה.
- המפתח הציבורי (publishable) נמצא בקוד האתר. זה בסדר: הוא מיועד לדפדפן ומוגבל להוספה בלבד.

הפניות: supabase.com, פרויקט yinonz-bina-site, Table Editor, טבלה leads.

## מייל על כל פנייה (Netlify, פעם אחת)

1. Site configuration, אחר כך Forms, ולוחצים **Enable form detection**.
2. גוררים את ה־ZIP החדש של האתר.
3. Site configuration, אחר כך Notifications, אחר כך Emails and webhooks: תחת Form submission notifications מוסיפים התראת מייל ל־yenon853@gmail.com.
