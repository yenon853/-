# התקנת סביבת HyperFrames + Claude Code על Windows
# הרצה: קליק ימני על הקובץ -> Run with PowerShell
# או מתוך PowerShell:  powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1
#
# הסקריפט מתקין רק מהמקורות הרשמיים:
#   Node.js LTS, FFmpeg (Gyan), Python 3.12, Git  - דרך winget
#   HyperFrames Skills + Chrome Headless Shell     - דרך npx (חבילת hyperframes הרשמית של heygen-com)
# כל שלב מודפס לפני שהוא רץ. אם שלב נכשל, הסקריפט עוצר ומציג את השגיאה.

$ErrorActionPreference = "Stop"

function Step($title) { Write-Host ""; Write-Host "=== $title ===" -ForegroundColor Cyan }
function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Ver($cmd, $args) { try { & $cmd $args 2>&1 | Select-Object -First 1 } catch { "לא נמצא" } }

Step "1. בדיקה: מה כבר מותקן"
"{0,-12} {1}" -f "Node.js:",  (Ver node "--version")
"{0,-12} {1}" -f "FFmpeg:",   (Ver ffmpeg "-version")
"{0,-12} {1}" -f "FFprobe:",  (Ver ffprobe "-version")
"{0,-12} {1}" -f "Python:",   (Ver python "--version")
"{0,-12} {1}" -f "Git:",      (Ver git "--version")

if (-not (Have winget)) {
    Write-Host "winget לא נמצא. התקן 'App Installer' מחנות Microsoft ואז הרץ שוב." -ForegroundColor Red
    exit 1
}

Step "2. התקנה דרך winget (מדלג על מה שכבר מותקן)"
$packages = @(
    @{ id = "OpenJS.NodeJS.LTS";  check = "node";   name = "Node.js LTS (22+)" },
    @{ id = "Gyan.FFmpeg";        check = "ffmpeg"; name = "FFmpeg + FFprobe" },
    @{ id = "Python.Python.3.12"; check = "python"; name = "Python 3.12" },
    @{ id = "Git.Git";            check = "git";    name = "Git" }
)
$installedSomething = $false
foreach ($p in $packages) {
    if (Have $p.check) {
        Write-Host "  כבר קיים: $($p.name)" -ForegroundColor Green
    } else {
        Write-Host "  מתקין: $($p.name)  ($($p.id))" -ForegroundColor Yellow
        winget install -e --id $p.id --accept-package-agreements --accept-source-agreements
        $installedSomething = $true
    }
}

if ($installedSomething) {
    Write-Host ""
    Write-Host "הותקנו כלים חדשים. סגור את החלון הזה, פתח PowerShell חדש והרץ את הסקריפט שוב." -ForegroundColor Yellow
    Write-Host "(טרמינל חדש נדרש כדי שהמחשב ימצא את הפקודות החדשות)" -ForegroundColor Yellow
    exit 0
}

Step "3. אימות גרסאות"
$nodeMajor = [int]((node --version) -replace '^v(\d+).*', '$1')
if ($nodeMajor -lt 22) { Write-Host "Node.js חייב להיות גרסה 22 ומעלה (נמצא $(node --version))" -ForegroundColor Red; exit 1 }
node --version; npm --version; ffmpeg -version | Select-Object -First 1; ffprobe -version | Select-Object -First 1; python --version; git --version

Step "4. התקנת ה-Skills של HyperFrames ל-Claude Code"
npx -y skills add heygen-com/hyperframes -g -y

Step "5. הורדת Chrome Headless Shell (הדפדפן שמרנדר את הסרטונים)"
npx -y hyperframes browser ensure

Step "6. npx hyperframes doctor"
Write-Host "בדיקות חובה: Node.js, FFmpeg, FFprobe, Chrome. שורות optional (whisper-cpp, Kokoro, MusicGen, Docker) לא חובה." -ForegroundColor Gray
npx -y hyperframes doctor

Step "סיום"
Write-Host "סגור את Claude Code ופתח אותו מחדש כדי שה-Skills ייטענו." -ForegroundColor Green
Write-Host "פרויקט חדש:  npx hyperframes init שם-הפרויקט" -ForegroundColor Green
