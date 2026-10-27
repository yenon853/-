# REVIEW: סרטון תדמית אנכי (9:16) · ינון זנו

Output: `renders/yinon-zano-promo-vertical.mp4`: 1080x1920, 30 fps, 47.4 s.
Request: "מותאם לנייד, ולקחת את זה מיליון צעדים קדימה באנימציות".

## What it is
A vertical recomposition of the v2 marketing film (`../my-video`), not a squeezed copy:
- **Real mobile screens:** the lomda was captured as it renders on a phone (a 980 px layout, captured at 2.5x so the punch-ins stay sharp). Every tap shows the lomda's own next state.
- **Social-safe layout:** every word and every product card sits between 168 and 1330 px. Below that there is only the brand's animated circuit motif.
- **Animation:**
  - letter-by-letter springs, masked line rises and slam-ins with shake
  - live labelling of the sentence with stickers (נשוא / נושא / תוספות)
  - a 3D flip of the cover card, rotating rays and sparkle stars
  - real taps with a touch indicator; cards fly in, pop and are zoomed through
  - deterministic confetti on correct answers, the "משוב מיידי" stamp, and a punch-in on "הנהלת בית הספר | אישרה" with its two labels
  - "+1" flying to the lomda's own counter
  - a scan bar over the student's essay, then the lomda's syntactic analysis of it
  - a 39 counter with a ring burst, and the 7 real chapter pills dropping in
  - the logo explained (face = בינה אנושית, circuits = יתרון טכנולוגי) and assembled into a stacked lockup
  - three brand-colour wipes between scenes
- **Grounds:** light only (white, mint, bright teal, amber, pink tint, grey-mint).

## Measured / looked
- `check`: ok. Frames looked at for every scene. Fixed: stickers covering words, a title crowding its band, a label over the lomda's text, a sticker over a title.
- Audio: 48 effects; hits measured at the taps and pops (e.g. 17.43, 18.14, 18.84, 19.54, 20.23 s for the five marking taps). −23.2 LUFS, true peak −7.4 dBTP, no clipping. **Measured, not heard.**

## Kept on purpose
- `dead_stretch` 17–20.5 s: the marking scene changes state on every tap there; the sampler misses image swaps.
- `line_unread` on "אינטראקטיביים": the check counts each animated letter as a word.

## Open
- No music and no narration: no music or voice service is reachable from this environment. The narration script in `../my-video/VOICEOVER.md` was timed for the landscape cut and needs retiming for this one.
- No contact line on the end card: none was given.
- The UI text inside the product cards is small on a phone; the big titles and stickers carry the message.
