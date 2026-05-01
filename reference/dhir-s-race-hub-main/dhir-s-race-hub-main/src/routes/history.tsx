import { createFileRoute } from "@tanstack/react-router";
import { PageShell } from "@/components/PageShell";
import { Checker } from "@/components/Checker";
import { RACES, driverByCode } from "@/lib/data";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "Race History — Dhir's Pit Wall" },
      { name: "description", content: "Editorial recap of every completed 2026 Formula One race." },
      { property: "og:title", content: "Race History — Dhir's Pit Wall" },
      { property: "og:description", content: "Editorial recap of every 2026 race." },
    ],
  }),
  component: HistoryPage,
});

function HistoryPage() {
  const completed = RACES.filter((r) => r.status === "completed");
  const totalRaces = RACES.length;
  const progress = (completed.length / totalRaces) * 100;

  return (
    <PageShell>
      {/* TIMELINE */}
      <section className="px-6 md:px-16 pt-12 pb-6">
        <div className="text-tag mb-3">Season Progress</div>
        <div className="relative h-1 bg-black/10 my-8">
          <div className="absolute h-full bg-[var(--redorange)]" style={{ width: `${progress}%` }} />
          <div className="absolute inset-0 flex justify-between -top-[3px]">
            {RACES.map((r) => (
              <div
                key={r.round}
                className={`w-2 h-2 rotate-45 ${r.status === "completed" ? "bg-[var(--redorange)]" : r.status === "next" ? "bg-[var(--ink)]" : "bg-black/30"}`}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between font-mono text-[8px] md:text-[10px] tracking-widest opacity-60">
          {RACES.map((r) => (
            <div key={r.round} className="text-center" style={{ width: `${100 / RACES.length}%` }}>
              R{String(r.round).padStart(2, "0")}
            </div>
          ))}
        </div>
      </section>

      <Checker />

      {/* HERO */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-4">2026 Season Archive</div>
        <h1 className="font-poster text-7xl md:text-[10rem] leading-[0.85] tracking-wider">
          RACE <span className="text-[var(--redorange)] italic">HISTORY</span>
        </h1>
        <p className="mt-6 font-serif italic text-xl md:text-2xl max-w-2xl">
          Five rounds in. The championship has already torn itself open and stitched itself shut twice.
        </p>
      </section>

      {completed.map((r, idx) => {
        const isHam = r.winner === "HAM";
        return (
          <div key={r.round}>
            <Checker />
            <RaceSection race={r} isHam={isHam} index={idx} />
          </div>
        );
      })}
    </PageShell>
  );
}

const HEROES = [
  "linear-gradient(135deg, #1a1a1a 0%, #3a1a1a 50%, #1a1a1a 100%)",
  "linear-gradient(135deg, #2a1a1a 0%, #1a1a1a 60%, #4a1010 100%)",
  "linear-gradient(160deg, #1a1a2a 0%, #1a1a1a 50%, #2a1a1a 100%)",
  "linear-gradient(45deg, #2a1010 0%, #1a1a1a 50%, #1a1010 100%)",
  "linear-gradient(135deg, #1a1a1a 0%, #2a2a1a 50%, #1a1010 100%)",
];

function RaceSection({ race, isHam, index }: { race: typeof RACES[0]; isHam: boolean; index: number }) {
  return (
    <section className="px-6 md:px-16 py-16">
      <div className="text-tag mb-3">Round {String(race.round).padStart(2, "0")} · {race.flag} {race.country}</div>
      <h2 className="font-poster text-5xl md:text-8xl leading-[0.9] tracking-wider mb-6">
        {race.name.toUpperCase()}
      </h2>

      {/* hero block */}
      <div
        className="relative aspect-[16/7] w-full grayscale"
        style={{ background: HEROES[index % HEROES.length] }}
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="font-poster text-[20vw] md:text-[14rem] text-white/5 tracking-widest leading-none">
            {race.flag}
          </div>
        </div>
        <div className="absolute bottom-4 left-4 font-mono text-[10px] uppercase tracking-widest text-white/50">
          {race.circuit}
        </div>
        {isHam && (
          <div className="absolute top-6 right-6 bg-[var(--redorange)] text-white px-4 py-2 font-display font-bold uppercase tracking-[0.2em] text-sm">
            HAM WINS ⭐
          </div>
        )}
      </div>

      {/* podium */}
      {race.podium && (
        <div className="grid grid-cols-3 gap-6 mt-10 pb-8 border-b border-black/15">
          {race.podium.map((code, i) => {
            const d = driverByCode(code);
            return (
              <div key={code} style={{ borderLeft: `4px solid ${d.color}` }} className="pl-4">
                <div className="font-mono text-xs opacity-60">P{i + 1}</div>
                <div className="font-poster text-3xl md:text-5xl mt-1 tracking-wider">
                  {d.code}
                </div>
                <div className="font-display font-bold uppercase text-sm">{d.name}</div>
                <div className="text-[10px] uppercase tracking-widest opacity-60">{d.team}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
        {[
          { l: "Date", v: new Date(race.date).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) },
          { l: "Laps", v: String(race.laps) },
          { l: "Length", v: `${race.lengthKm.toFixed(3)} km` },
          { l: "Fastest Lap", v: race.fastestLap ?? "—" },
        ].map((x) => (
          <div key={x.l} className="border-t border-black/40 pt-3">
            <div className="text-tag">{x.l}</div>
            <div className="font-mono text-xl md:text-2xl mt-1">{x.v}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
