import React from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { type Driver, type Race, driverByCode, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "Race Archive - Dhir's Pit Wall" },
      { name: "description", content: "Archive of completed 2026 races and the season path." },
    ],
  }),
  component: HistoryPage,
});

function HistoryPage() {
  const { races, drivers } = useSiteData();
  const completed = races.filter((race) => race.status === "completed");
  const cancelled = races.filter((race) => race.status === "cancelled");
  const upcomingCount = races.length - completed.length - cancelled.length;
  const progress = (completed.length / races.length) * 100;

  return (
    <PageShell>
      <section className="px-4 md:px-8 pt-10 pb-4">
        <div className="text-tag mb-2">Season Progress</div>
        <div className="relative h-1 bg-black/10 my-6">
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
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">2026 Season Archive</div>
        <h1 className="font-poster text-6xl md:text-[8rem] leading-[0.85] tracking-wider">
          RACE <span className="text-[var(--redorange)] italic">HISTORY</span>
        </h1>
        <p className="mt-4 font-serif italic text-lg md:text-xl max-w-3xl leading-relaxed">
          {completed.length} rounds are in the books, {cancelled.length} weekends were cancelled, and {upcomingCount} races remain on the calendar.
        </p>
        
        {cancelled.length > 0 && (
          <div className="mt-8 grid md:grid-cols-2 gap-3 max-w-4xl">
            {cancelled.map((race) => (
              <div key={race.round} className="border border-black/15 p-4">
                <div className="text-tag">Round {String(race.round).padStart(2, "0")} Cancelled</div>
                <div className="font-display font-bold uppercase text-base mt-2">{race.name}</div>
                <p className="text-xs mt-1 opacity-70">{race.note}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {completed.map((race) => (
        <div key={race.round}>
          <Checker />
          <RaceSection race={race} drivers={drivers} />
        </div>
      ))}
    </PageShell>
  );
}

function RaceSection({ race, drivers }: { race: Race; drivers: Driver[] }) {
  const [imageError, setImageError] = React.useState(false);
  const winner = race.winner ? driverByCode(race.winner, drivers) : null;
  const winnerColor = winner ? winner.color : "var(--charcoal)";
  const gradient = `linear-gradient(135deg, color-mix(in srgb, ${winnerColor} 15%, black), black)`;

  return (
    <section className="px-4 md:px-8 py-10">
      <div className="text-tag mb-2">
        Round {String(race.round).padStart(2, "0")} . {race.flag} {race.country}
      </div>
      <h2 className="font-poster text-4xl md:text-6xl leading-[0.9] tracking-wider mb-5">
        {race.name.toUpperCase()}
      </h2>

      <div className="relative aspect-[16/6] md:aspect-[16/5] w-full overflow-hidden bg-black group">
        {race.winnerImage && !imageError ? (
          <>
            <img 
              src={race.winnerImage} 
              alt={`${race.name} winner`}
              onError={() => setImageError(true)}
              className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-luminosity group-hover:mix-blend-normal transition-all duration-700" 
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent" />
          </>
        ) : (
          <div className="absolute inset-0" style={{ background: gradient }} />
        )}
        
        <div className="absolute bottom-4 left-4 font-mono text-[9px] uppercase tracking-widest text-white/50 z-10">
          {race.circuit}
        </div>
        
        {winner && (
          <div className="absolute top-4 right-4 text-white px-3 py-1.5 font-display font-bold uppercase tracking-[0.2em] text-xs z-10" style={{ backgroundColor: winnerColor }}>
            {winner.code} WINS
          </div>
        )}
      </div>

      {race.podium && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8 pb-6 border-b border-black/15">
          {race.podium.map((code, indexInPodium) => {
            const driver = driverByCode(code, drivers);
            return (
              <div key={code} style={{ borderLeft: `3px solid ${driver.color}` }} className="pl-3">
                <div className="font-mono text-[10px] opacity-60">P{indexInPodium + 1}</div>
                <div className="font-poster text-2xl md:text-4xl mt-1 tracking-wider">
                  {driver.code}
                </div>
                <div className="font-display font-bold uppercase text-xs">{driver.name}</div>
                <div className="text-[9px] uppercase tracking-widest opacity-60">{driver.team}</div>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
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
          <div key={item.label} className="border-t border-black/20 pt-2">
            <div className="text-tag">{item.label}</div>
            <div className="font-mono text-lg md:text-xl mt-1">{item.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
