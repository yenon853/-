# סרטון תדמית – מקיף י' (HyperFrames)

סרטון של 30 שניות, ‎1920×1080, ‏30fps. הקובץ המוכן: `mekif-yud-promo.mp4`.

## מבנה
| סצנה | קובץ | זמן |
|---|---|---|
| פתיחה – "המחר מתחיל היום." | `compositions/open.html` | 0–4.6 |
| לומדים / חוקרים / יוצרים / מובילים | `compositions/verbs.html` | 4.6–10.2 |
| מה מניע אותנו – 3 ערכים | `compositions/values.html` | 10.2–18.6 |
| נבחרת ה-AI | `compositions/ai.html` | 18.6–23.8 |
| סיום – לוגו, ראשון לציון, אתר | `compositions/endcard.html` | 23.8–30 |

## עריכה ורינדור
```bash
npx hyperframes preview      # תצוגה מקדימה בדפדפן
npm run check                # בדיקה
npx hyperframes render --output mekif-yud-promo.mp4
```
הטקסטים כתובים ישירות בקבצי הסצנות. פונט: Heebo (‏`assets/fonts`). GSAP מקומי (‏`assets/vendor`).
