import { useMemo } from "react";

export function SakuraOverlay() {
  const petals = useMemo(
    () =>
      Array.from({ length: 18 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 20,
        duration: 14 + Math.random() * 18,
        size: 6 + Math.random() * 10,
        opacity: 0.3 + Math.random() * 0.35,
      })),
    []
  );
  return (
    <div className="sakura-overlay" aria-hidden>
      {petals.map((p) => (
        <span
          key={p.id}
          className="sakura"
          style={{
            left: `${p.left}%`,
            width: p.size,
            height: p.size,
            opacity: p.opacity,
            animationDuration: `${p.duration}s`,
            animationDelay: `-${p.delay}s`,
          }}
        />
      ))}
    </div>
  );
}
