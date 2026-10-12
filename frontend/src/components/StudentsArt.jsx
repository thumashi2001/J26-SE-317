// A friendly original illustration: two students with books in front of a campus building.
export default function StudentsArt() {
  return (
    <svg viewBox="0 0 480 340" role="img" aria-label="Two smiling students holding books in front of a campus building" className="students-art">
      <defs>
        <linearGradient id="sa-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#bfe9dd" />
          <stop offset="1" stopColor="#f4fbf8" />
        </linearGradient>
      </defs>
      <rect width="480" height="340" rx="22" fill="url(#sa-sky)" />
      <circle cx="412" cy="58" r="30" fill="#ffd36b" />
      <circle cx="412" cy="58" r="42" fill="#ffd36b" opacity="0.28" />

      {/* campus building */}
      <rect x="86" y="96" width="308" height="190" rx="6" fill="#dfe9f1" />
      <rect x="74" y="80" width="332" height="24" rx="5" fill="#0e2238" />
      <rect x="196" y="58" width="88" height="30" rx="5" fill="#1b3a59" />
      {[104, 150, 196, 242, 288, 334].map((x) => (
        <g key={x}>
          <rect x={x} y="116" width="28" height="30" rx="4" fill="#9fd8c8" />
          <rect x={x} y="162" width="28" height="30" rx="4" fill="#9fd8c8" />
        </g>
      ))}
      {[104, 144, 308, 348].map((x) => (
        <rect key={x} x={x} y="206" width="22" height="80" fill="#c9d8e4" />
      ))}
      <rect x="214" y="214" width="52" height="72" rx="5" fill="#35495a" />

      {/* trees and ground */}
      <rect x="54" y="226" width="8" height="60" fill="#7a5a3a" />
      <circle cx="58" cy="214" r="30" fill="#3aa579" />
      <rect x="418" y="232" width="8" height="54" fill="#7a5a3a" />
      <circle cx="422" cy="220" r="26" fill="#2f9468" />
      <rect x="0" y="286" width="480" height="54" fill="#8fd3c0" />
      <ellipse cx="240" cy="318" rx="130" ry="9" fill="#0e2238" opacity="0.1" />

      {/* girl */}
      <path d="M138 150 Q138 112 170 112 Q202 112 202 150 L207 216 Q170 228 133 216 Z" fill="#2b1b17" />
      <rect x="154" y="262" width="12" height="46" rx="5" fill="#c98a5b" />
      <rect x="174" y="262" width="12" height="46" rx="5" fill="#c98a5b" />
      <ellipse cx="160" cy="310" rx="11" ry="5" fill="#0e2238" />
      <ellipse cx="180" cy="310" rx="11" ry="5" fill="#0e2238" />
      <path d="M142 184 Q170 172 198 184 L208 266 L132 266 Z" fill="#0f9a78" />
      <rect x="163" y="170" width="14" height="14" rx="4" fill="#c98a5b" />
      <circle cx="170" cy="150" r="26" fill="#c98a5b" />
      <path d="M144 148 Q148 120 170 121 Q192 120 196 148 Q184 132 144 148 Z" fill="#2b1b17" />
      <circle cx="161" cy="153" r="2.6" fill="#2b1b17" />
      <circle cx="179" cy="153" r="2.6" fill="#2b1b17" />
      <path d="M162 164 Q170 172 178 164" fill="none" stroke="#7a2e2e" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M147 194 Q134 224 156 230" fill="none" stroke="#c98a5b" strokeWidth="9" strokeLinecap="round" />
      <path d="M193 194 Q206 224 184 230" fill="none" stroke="#c98a5b" strokeWidth="9" strokeLinecap="round" />
      <rect x="148" y="208" width="44" height="12" rx="2" fill="#f4b942" />
      <rect x="150" y="220" width="40" height="11" rx="2" fill="#e0584f" />
      <rect x="152" y="231" width="36" height="10" rx="2" fill="#7aa6c9" />

      {/* boy */}
      <rect x="288" y="262" width="17" height="46" rx="5" fill="#35495a" />
      <rect x="315" y="262" width="17" height="46" rx="5" fill="#35495a" />
      <ellipse cx="296" cy="310" rx="13" ry="5" fill="#0e2238" />
      <ellipse cx="324" cy="310" rx="13" ry="5" fill="#0e2238" />
      <path d="M280 186 Q310 174 340 186 L348 266 L272 266 Z" fill="#1b3a59" />
      <path d="M298 178 L310 194 L322 178 Z" fill="#ffffff" />
      <path d="M292 184 L300 262" stroke="#087a63" strokeWidth="6" strokeLinecap="round" />
      <rect x="303" y="170" width="14" height="14" rx="4" fill="#b87444" />
      <circle cx="310" cy="150" r="26" fill="#b87444" />
      <path d="M284 148 Q283 117 310 117 Q337 117 336 148 Q326 131 310 134 Q294 131 284 148 Z" fill="#1a1a1a" />
      <circle cx="301" cy="153" r="2.6" fill="#1a1a1a" />
      <circle cx="319" cy="153" r="2.6" fill="#1a1a1a" />
      <path d="M301 164 Q310 173 319 164" fill="none" stroke="#6b2a2a" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M283 194 Q262 182 266 156" fill="none" stroke="#b87444" strokeWidth="9" strokeLinecap="round" />
      <circle cx="266" cy="152" r="7" fill="#b87444" />
      <path d="M338 194 Q354 224 336 232" fill="none" stroke="#b87444" strokeWidth="9" strokeLinecap="round" />
      <rect x="322" y="224" width="40" height="11" rx="2" fill="#f4b942" />
      <rect x="320" y="235" width="42" height="11" rx="2" fill="#0f9a78" />

      {/* small sparkles */}
      <path d="M118 62 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4 z" fill="#ffd36b" />
      <path d="M356 100 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3 z" fill="#ffffff" />
    </svg>
  );
}
