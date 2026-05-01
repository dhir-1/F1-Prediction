export function BlossomBranch({ className = "", flip = false }: { className?: string; flip?: boolean }) {
  return (
    <svg
      viewBox="0 0 240 160"
      className={className}
      style={{ transform: flip ? "scaleX(-1)" : undefined }}
      aria-hidden
    >
      <g fill="none" stroke="#3a2018" strokeWidth="2" opacity="0.55">
        <path d="M5 150 C 60 130, 90 95, 130 70 S 200 30, 235 10" />
        <path d="M70 115 C 80 100, 95 92, 110 90" />
        <path d="M150 60 C 165 50, 180 48, 195 50" />
      </g>
      {[
        [40, 142], [85, 110], [120, 80], [160, 55], [200, 35], [225, 18],
        [105, 92], [185, 48], [70, 130], [145, 70],
      ].map(([cx, cy], i) => (
        <g key={i} opacity="0.7">
          <circle cx={cx} cy={cy} r="6" fill="#f7b8c8" />
          <circle cx={cx + 4} cy={cy - 3} r="5" fill="#e8628a" opacity="0.7" />
          <circle cx={cx - 3} cy={cy + 3} r="4" fill="#f7b8c8" />
          <circle cx={cx} cy={cy} r="1.4" fill="#fff3a8" />
        </g>
      ))}
    </svg>
  );
}
