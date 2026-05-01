import { createFileRoute } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { type Driver, type Race, driverByCode, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "Race Archive - Dhir's Pit Wall" },
      { name: "description", content: "Archive of completed 2026 races and the season path into Miami." },
      { property: "og:title", content: "Race Archive - Dhir's Pit Wall" },
      { property: "og:description", content: "Archive of completed 2026 races." },
    ],
  }),
  component: HistoryPage,
});

function HistoryPage() {
  const { races, drivers } = useSiteData();
  const completed = races.filter((race) => race.status === "completed");
  const cancelled = races.filter((race) => race.status === "cancelled");
  const totalRaces = races.length;
  const progress = (completed.length / totalRaces) * 100;

  return (
    <PageShell>
      <section className="px-6 md:px-16 pt-12 pb-6">
        <div className="text-tag mb-3">Season Progress</div>
        <div className="relative h-1 bg-black/10 my-8">
          <div className="absolute h-full bg-[var(--redorange)]" style={{ width: `${progress}%` }} />
          <div className="absolute inset-0 flex justify-between -top-[3px]">
            {races.map((race) => (
              <div
                key={race.round}
                className={`w-2 h-2 rotate-45 ${
                  race.status === "completed"
                    ? "bg-[var(--redorange)]"
                    : race.status === "next"
                      ? "bg-[var(--ink)]"
                      : race.status === "cancelled"
                        ? "bg-[var(--rose)]"
                        : "bg-black/30"
                }`}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between font-mono text-[8px] md:text-[10px] tracking-widest opacity-60">
          {races.map((race) => (
            <div key={race.round} className="text-center" style={{ width: `${100 / races.length}%` }}>
              R{String(race.round).padStart(2, "0")}
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-4">2026 Season Archive</div>
        <h1 className="font-poster text-7xl md:text-[10rem] leading-[0.85] tracking-wider">
          RACE <span className="text-[var(--redorange)] italic">HISTORY</span>
        </h1>
        <p className="mt-6 font-serif italic text-xl md:text-2xl max-w-3xl">
          Three rounds are in the book, two early weekends were cancelled, and Miami sits next in
          line with the first model-backed call of the season.
        </p>
        {cancelled.length > 0 && (
          <div className="mt-8 grid md:grid-cols-2 gap-4 max-w-4xl">
            {cancelled.map((race) => (
              <div key={race.round} className="border border-black/15 p-5">
                <div className="text-tag">Round {String(race.round).padStart(2, "0")} Cancelled</div>
                <div className="font-display font-bold uppercase text-lg mt-2">{race.name}</div>
                <p className="text-sm mt-2 opacity-70">{race.note}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {completed.map((race, index) => (
        <div key={race.round}>
          <Checker />
          <RaceSection race={race} drivers={drivers} index={index} />
        </div>
      ))}
    </PageShell>
  );
}

const HEROES = [
  "linear-gradient(135deg, #1a1a1a 0%, #3a1a1a 50%, #1a1a1a 100%)",
  "linear-gradient(135deg, #2a1a1a 0%, #1a1a1a 60%, #4a1010 100%)",
  "linear-gradient(160deg, #1a1a2a 0%, #1a1a1a 50%, #2a1a1a 100%)",
];

function RaceSection({
  race,
  drivers,
  index,
}: {
  race: Race;
  drivers: Driver[];
  index: number;
}) {
  const isHamiltonWin = race.winner === "HAM";

  return (
    <section className="px-6 md:px-16 py-16">
      <div className="text-tag mb-3">
        Round {String(race.round).padStart(2, "0")} . {race.flag} {race.country}
      </div>
      <h2 className="font-poster text-5xl md:text-8xl leading-[0.9] tracking-wider mb-6">
        {race.name.toUpperCase()}
      </h2>

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
        {isHamiltonWin && (
          <div className="absolute top-6 right-6 bg-[var(--redorange)] text-white px-4 py-2 font-display font-bold uppercase tracking-[0.2em] text-sm">
            HAM WINS
          </div>
        )}
      </div>

      {race.podium && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-10 pb-8 border-b border-black/15">
          {race.podium.map((code, indexInPodium) => {
            const driver = driverByCode(code, drivers);
            return (
              <div key={code} style={{ borderLeft: `4px solid ${driver.color}` }} className="pl-4">
                <div className="font-mono text-xs opacity-60">P{indexInPodium + 1}</div>
                <div className="font-poster text-3xl md:text-5xl mt-1 tracking-wider">
                  {driver.code}
                </div>
                <div className="font-display font-bold uppercase text-sm">{driver.name}</div>
                <div className="text-[10px] uppercase tracking-widest opacity-60">{driver.team}</div>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
        {[
          {
            label: "Date",
            value: new Date(race.date).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            }),
          },
          { label: "Laps", value: String(race.laps) },
          { label: "Length", value: `${race.lengthKm.toFixed(3)} km` },
          { label: "Fastest Lap", value: race.fastestLap ?? "-" },
        ].map((item) => (
          <div key={item.label} className="border-t border-black/40 pt-3">
            <div className="text-tag">{item.label}</div>
            <div className="font-mono text-xl md:text-2xl mt-1">{item.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
