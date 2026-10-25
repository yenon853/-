import { Sparkles, Mic } from 'lucide-react';
import { EFRAT_STAGES } from './efratConfig.js';

function StatusBubble({ status, text, tone }) {
  if (!status) return null;
  const Icon = status === 'listening' ? Mic : Sparkles;
  return (
    <div
      className={`absolute -top-1 right-4 bg-white/95 border-2 px-3 py-1 rounded-full shadow-md flex items-center gap-1.5 text-xs font-bold ${tone} ${
        status === 'listening' ? 'animate-pulse' : 'animate-bounce'
      }`}
    >
      <Icon className={`w-3.5 h-3.5 ${status === 'listening' ? 'text-rose-500' : 'text-amber-500'}`} />
      <span>{text}</span>
    </div>
  );
}

function Aura({ activeStage, isSpeaking }) {
  return (
    <div
      className={`absolute w-44 h-44 rounded-full blur-2xl transition-all duration-700 ${EFRAT_STAGES[activeStage].aura} ${
        isSpeaking ? 'opacity-80 scale-110 animate-pulse' : 'opacity-50'
      }`}
    />
  );
}

export function EfratCharacterSVG({ activeStage, isSpeaking, status, statusText }) {
  return (
    <div className="relative flex flex-col items-center justify-center select-none">
      <Aura activeStage={activeStage} isSpeaking={isSpeaking} />
      <svg
        viewBox="0 0 260 250"
        role="img"
        aria-label="אפרת"
        className={`relative w-44 h-44 sm:w-52 sm:h-52 drop-shadow-md transition-transform duration-500 ${
          isSpeaking ? 'scale-105' : 'hover:scale-102'
        }`}
      >
        <defs>
          <radialGradient id="furGrad" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="65%" stopColor="#0284c7" />
            <stop offset="100%" stopColor="#0369a1" />
          </radialGradient>
          <linearGradient id="vestGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#fef3c7" />
            <stop offset="100%" stopColor="#fde68a" />
          </linearGradient>
          <radialGradient id="glassGrad" cx="35%" cy="35%" r="60%">
            <stop offset="0%" stopColor="#e0f2fe" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#7dd3fc" stopOpacity="0.4" />
          </radialGradient>
        </defs>

        <ellipse cx="130" cy="236" rx="68" ry="9" fill="#0f172a" opacity="0.12" />

        <g>
          <rect x="72" y="210" width="42" height="22" rx="11" fill="#1d4ed8" />
          <path d="M 72 224 Q 93 228 114 224 L 114 230 Q 93 234 72 230 Z" fill="#ffffff" />
          <line x1="86" y1="214" x2="98" y2="214" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
          <rect x="146" y="210" width="42" height="22" rx="11" fill="#1d4ed8" />
          <path d="M 146 224 Q 167 228 188 224 L 188 230 Q 167 234 146 230 Z" fill="#ffffff" />
          <line x1="162" y1="214" x2="174" y2="214" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
        </g>

        <path d="M 190 135 Q 225 125 234 108 Q 242 98 232 90 Q 222 86 212 100 Q 198 114 185 120 Z" fill="url(#furGrad)" />
        <circle cx="230" cy="96" r="11" fill="#38bdf8" />

        <path
          d="M 130 22 C 142 12, 158 18, 154 30 C 172 24, 196 38, 192 58 C 210 68, 216 95, 206 115 C 218 140, 212 185, 192 204 C 175 218, 85 218, 68 204 C 48 185, 42 140, 54 115 C 44 95, 50 68, 68 58 C 64 38, 88 24, 106 30 C 102 18, 118 12, 130 22 Z"
          fill="url(#furGrad)"
        />

        <path d="M 122 25 Q 130 4 146 14 Q 138 24 136 28 Z" fill="#38bdf8" />
        <path d="M 112 28 Q 115 10 130 16 Q 125 24 124 29 Z" fill="#0ea5e9" />

        <path d="M 55 72 Q 35 65 44 86 Q 50 92 56 88 Z" fill="#0284c7" />
        <path d="M 205 72 Q 225 65 216 86 Q 210 92 204 88 Z" fill="#0284c7" />

        <ellipse cx="84" cy="108" rx="13" ry="8" fill="#fb7185" opacity="0.45" />
        <ellipse cx="176" cy="108" rx="13" ry="8" fill="#fb7185" opacity="0.45" />

        <g>
          <ellipse cx="102" cy="86" rx="17" ry="19" fill="#ffffff" />
          <ellipse cx="104" cy="87" rx="11.5" ry="13" fill="#451a03" />
          <circle cx="104" cy="87" r="6" fill="#000000" />
          <circle cx="99" cy="81" r="4.5" fill="#ffffff" />
          <circle cx="108" cy="92" r="2" fill="#ffffff" />
          <path d="M 86 64 Q 102 57 115 65" fill="none" stroke="#0369a1" strokeWidth="4" strokeLinecap="round" />
          <ellipse cx="158" cy="86" rx="17" ry="19" fill="#ffffff" />
          <ellipse cx="156" cy="87" rx="11.5" ry="13" fill="#451a03" />
          <circle cx="156" cy="87" r="6" fill="#000000" />
          <circle cx="151" cy="81" r="4.5" fill="#ffffff" />
          <circle cx="160" cy="92" r="2" fill="#ffffff" />
          <path d="M 145 65 Q 158 57 174 64" fill="none" stroke="#0369a1" strokeWidth="4" strokeLinecap="round" />
        </g>

        <ellipse cx="130" cy="99" rx="9" ry="6" fill="#0369a1" />
        <ellipse cx="128" cy="97" rx="4" ry="2" fill="#7dd3fc" />

        {isSpeaking ? (
          <path d="M 110 112 Q 130 132 150 112 Q 130 120 110 112 Z" fill="#9f1239" stroke="#0369a1" strokeWidth="2">
            <animate
              attributeName="d"
              dur="0.35s"
              repeatCount="indefinite"
              values="M 110 112 Q 130 132 150 112 Q 130 120 110 112 Z;M 112 112 Q 130 124 148 112 Q 130 116 112 112 Z;M 110 112 Q 130 132 150 112 Q 130 120 110 112 Z"
            />
          </path>
        ) : (
          <g>
            <path d="M 110 111 Q 130 129 150 111 Z" fill="#881337" />
            <path d="M 118 119 Q 130 126 142 119" fill="#fb7185" />
            <path d="M 114 112 Q 130 116 146 112" stroke="#ffffff" strokeWidth="3.5" strokeLinecap="round" fill="none" />
          </g>
        )}

        <g>
          <path d="M 70 128 L 118 138 L 122 204 L 66 198 Q 58 164 70 128 Z" fill="url(#vestGrad)" stroke="#d97706" strokeWidth="2" />
          <path d="M 190 128 L 142 138 L 138 204 L 194 198 Q 202 164 190 128 Z" fill="url(#vestGrad)" stroke="#d97706" strokeWidth="2" />

          <rect x="77" y="138" width="32" height="27" rx="6" fill="#0284c7" stroke={activeStage === 0 ? '#ffffff' : 'none'} strokeWidth="2.5" />
          <rect x="83" y="145" width="20" height="14" rx="3" fill="#e0f2fe" />
          <circle cx="93" cy="152" r="4.5" fill="#0284c7" />

          <rect x="151" y="138" width="32" height="27" rx="6" fill="#9333ea" stroke={activeStage === 1 ? '#ffffff' : 'none'} strokeWidth="2.5" />
          <path d="M 160 155 Q 158 149 164 148 Q 167 143 173 147 Q 178 148 176 155 Z" fill="#f3e8ff" />

          <rect x="77" y="170" width="32" height="27" rx="6" fill="#e11d48" stroke={activeStage === 2 ? '#ffffff' : 'none'} strokeWidth="2.5" />
          <path d="M 93 190 L 85 182 A 4.5 4.5 0 0 1 93 177 A 4.5 4.5 0 0 1 101 182 Z" fill="#ffe4e6" />

          <rect x="151" y="170" width="32" height="27" rx="6" fill="#16a34a" stroke={activeStage === 3 ? '#ffffff' : 'none'} strokeWidth="2.5" />
          <circle cx="167" cy="185" r="6.5" fill="#dcfce7" />

          <path d="M 130 172 L 120 162 A 6 6 0 0 1 130 154 A 6 6 0 0 1 140 162 Z" fill="#ef4444" stroke="#b91c1c" strokeWidth="1.5" />
        </g>

        <g>
          <line x1="56" y1="122" x2="38" y2="148" stroke="#1e3a8a" strokeWidth="9" strokeLinecap="round" />
          <circle cx="50" cy="132" r="13" fill="#38bdf8" stroke="#0284c7" strokeWidth="2" />
          <circle cx="65" cy="95" r="24" fill="url(#glassGrad)" stroke="#d97706" strokeWidth="6" />
          <circle cx="65" cy="95" r="21" fill="none" stroke="#fef08a" strokeWidth="2" />
          <path d="M 52 84 Q 58 77 68 79" stroke="#ffffff" strokeWidth="3.5" strokeLinecap="round" fill="none" />
        </g>
      </svg>
      <StatusBubble status={status} text={statusText} tone="border-sky-200 text-sky-700" />
    </div>
  );
}

export function WiseGrandpaSVG({ activeStage, isSpeaking, status, statusText }) {
  return (
    <div className="relative flex flex-col items-center justify-center select-none">
      <Aura activeStage={activeStage} isSpeaking={isSpeaking} />
      <svg
        viewBox="0 0 260 250"
        role="img"
        aria-label="סבא חכם"
        className={`relative w-44 h-44 sm:w-52 sm:h-52 drop-shadow-md transition-transform duration-500 ${
          isSpeaking ? 'scale-105' : 'hover:scale-102'
        }`}
      >
        <ellipse cx="130" cy="236" rx="64" ry="8" fill="#0f172a" opacity="0.12" />
        <path d="M 65 225 Q 68 145 130 145 Q 192 145 195 225 Z" fill="#0d9488" stroke="#115e59" strokeWidth="3" />
        <polygon points="112,148 148,148 130,185" fill="#fef3c7" />
        <circle cx="130" cy="196" r="4" fill="#fde68a" />
        <circle cx="130" cy="212" r="4" fill="#fde68a" />

        <circle cx="96" cy="175" r="10" fill="#0284c7" stroke={activeStage === 0 ? '#fff' : 'none'} strokeWidth="2" />
        <circle cx="164" cy="175" r="10" fill="#9333ea" stroke={activeStage === 1 ? '#fff' : 'none'} strokeWidth="2" />
        <circle cx="96" cy="202" r="10" fill="#e11d48" stroke={activeStage === 2 ? '#fff' : 'none'} strokeWidth="2" />
        <circle cx="164" cy="202" r="10" fill="#16a34a" stroke={activeStage === 3 ? '#fff' : 'none'} strokeWidth="2" />

        <circle cx="76" cy="88" r="20" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
        <circle cx="184" cy="88" r="20" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
        <ellipse cx="130" cy="95" rx="52" ry="56" fill="#fed7aa" stroke="#fdba74" strokeWidth="2" />
        <circle cx="77" cy="98" r="11" fill="#fed7aa" />
        <circle cx="183" cy="98" r="11" fill="#fed7aa" />
        <path d="M 90 50 Q 130 32 170 50 Q 150 38 110 42 Z" fill="#f8fafc" />

        <path d="M 92 72 Q 106 64 118 72" stroke="#f8fafc" strokeWidth="7" strokeLinecap="round" fill="none" />
        <path d="M 142 72 Q 154 64 168 72" stroke="#f8fafc" strokeWidth="7" strokeLinecap="round" fill="none" />

        <circle cx="106" cy="88" r="6" fill="#334155" />
        <circle cx="104" cy="86" r="2" fill="#ffffff" />
        <circle cx="154" cy="88" r="6" fill="#334155" />
        <circle cx="152" cy="86" r="2" fill="#ffffff" />

        <circle cx="106" cy="88" r="16" fill="none" stroke="#d97706" strokeWidth="3.5" />
        <circle cx="154" cy="88" r="16" fill="none" stroke="#d97706" strokeWidth="3.5" />
        <line x1="122" y1="88" x2="138" y2="88" stroke="#d97706" strokeWidth="3.5" />

        <ellipse cx="130" cy="103" rx="9" ry="7" fill="#fb923c" />

        <path d="M 84 112 Q 82 158 130 162 Q 178 158 176 112 Q 155 124 130 120 Q 105 124 84 112 Z" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" />
        <path d="M 102 115 Q 130 105 158 115 Q 145 127 130 121 Q 115 127 102 115 Z" fill="#f1f5f9" />

        <path
          d={isSpeaking ? 'M 116 126 Q 130 140 144 126 Z' : 'M 116 126 Q 130 136 144 126'}
          fill={isSpeaking ? '#9f1239' : 'none'}
          stroke="#475569"
          strokeWidth="3"
          strokeLinecap="round"
        >
          {isSpeaking && (
            <animate
              attributeName="d"
              dur="0.4s"
              repeatCount="indefinite"
              values="M 116 126 Q 130 140 144 126 Z;M 118 126 Q 130 132 142 126 Z;M 116 126 Q 130 140 144 126 Z"
            />
          )}
        </path>
      </svg>
      <StatusBubble status={status} text={statusText} tone="border-teal-200 text-teal-800" />
    </div>
  );
}
