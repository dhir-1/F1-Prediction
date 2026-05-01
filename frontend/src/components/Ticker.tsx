import { useSiteData } from "@/lib/data";

export function Ticker() {
  const { drivers } = useSiteData();
  const items = [...drivers, ...drivers];

  return (
    <div
      className="relative bg-[var(--charcoal)] text-[var(--cream)] py-2 overflow-hidden border-b border-white/10"
      style={{
        maskImage:
          "linear-gradient(90deg, transparent 0, #000 60px, #000 calc(100% - 60px), transparent 100%)",
      }}
    >
      <div className="ticker-track whitespace-nowrap font-mono text-[11px] tracking-widest uppercase">
        {items.map((driver, index) => (
          <span key={`${driver.code}-${index}`} className="px-6 inline-flex items-center gap-2">
            <span className="text-[var(--redorange)] font-bold">{driver.code}</span>
            <span className="opacity-80">{driver.name}</span>
            <span className="opacity-40">.</span>
            <span className="opacity-60">{driver.team}</span>
            <span className="opacity-30 ml-4">/</span>
          </span>
        ))}
      </div>
    </div>
  );
}
