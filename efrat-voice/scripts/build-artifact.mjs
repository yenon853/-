// בונה גרסה של קובץ HTML יחיד לפרסום כעמוד ב-claude.ai (Claude הוא מוח השיחה, הקראה מהדפדפן).
// שימוש: npm run build:artifact -- <נתיב-פלט>
import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import path from 'node:path';

const outDir = 'dist-artifact';
execSync(`npx vite build --mode artifact --outDir ${outDir} --emptyOutDir`, { stdio: 'inherit' });

const assets = path.join(outDir, 'assets');
const files = readdirSync(assets);
const js = readFileSync(path.join(assets, files.find((f) => f.endsWith('.js'))), 'utf8').replace(/<\/script/gi, '<\\/script');
const css = readFileSync(path.join(assets, files.find((f) => f.endsWith('.css'))), 'utf8').replace(/<\/style/gi, '<\\/style');

const page = `<title>תשאלו את אפרת</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700;800;900&display=swap">
<style>${css}
html,body{background:#fffbeb;color:#1e293b}
</style>
<div id="root" dir="rtl" lang="he"></div>
<script type="module">${js}</script>
`;

const target = process.argv[2] || path.join(outDir, 'efrat-artifact.html');
writeFileSync(target, page);
console.log(`נכתב: ${target} (${(page.length / 1024).toFixed(0)}KB)`);
