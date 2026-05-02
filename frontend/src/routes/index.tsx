import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { BlossomBranch } from "@/components/BlossomBranch";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { constructorStandings, driverByCode, standings, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/")(  {
  head: () => ({
    meta: [
      { title: "Dashboard - Dhir's Pit Wall" },
      { name: "description", content: "2026 F1 season dashboard: next race, standings, predictions, and calendar." },
      { property: "og:title", content: "Dashboard - Dhir's Pit Wall" },
      { property: "og:description", content: "2026 F1 season dashboard." },
    ],
  }),
  component: Index,
});

function useCountdown(targetIso: string) {
  const [time, setTime] = useState({ d: 0, h: 0, m: 0, s: 0 });

  useEffect(() => {
    const target = new Date(targetIso).getTime();

    const tick = () => {
      const diff = Math.max(0, target - Date.now());
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff / 3600000) % 24);
      const m = Math.floor((diff / 60000) % 60);
      const s = Math.floor((diff / 1000) % 60);
      setTime({ d, h, m, s });
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [targetIso]);

  return time;
}

function Index() {
  const siteData = useSiteData();
  const drivers = standings(siteData.drivers);
  const constructors = constructorStandings(siteData.drivers);
  const next = siteData.races.find((race) => race.status === "next")!;
  const countdown = useCountdown(next.date);
  const maxConstructorPoints = Math.max(...constructors.map((c) => c.points));
  const predictions = siteData.predictions;
  const nextRacePrediction = predictions.find((p) => p.round === next.round);

  return (
    <PageShell>
      {/* ── Hero ── */}
      <section className="relative px-4 md:px-8 pt-10 pb-6 overflow-hidden">
        <BlossomBranch className="absolute top-0 left-0 w-40 md:w-64 opacity-50" />
        <BlossomBranch className="absolute top-0 right-0 w-40 md:w-64 opacity-50" flip />
        <div className="relative">
          <div className="text-tag mb-2">2026 Season . Race Predictions</div>
          <h1 className="font-poster italic leading-[0.85] text-[13vw] md:text-[7.5rem]">
            <span className="block">DHIR'S</span>
            <span className="block text-[var(--redorange)]">PIT WALL</span>
          </h1>
          <p className="font-display uppercase tracking-[0.3em] text-sm opacity-70 mt-3">
            Formula One . Machine Learning . Season Tracker
          </p>
        </div>
      </section>

      <Checker />

      {/* ── Next Race + Countdown ── */}
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-8 relative overflow-hidden">
        <SpeedLines />
        <div className="relative flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div>
            <div className="text-tag mb-1">Round {String(next.round).padStart(2, "0")} . Next Up</div>
            <h2 className="font-poster text-5xl md:text-7xl tracking-wider leading-none">
              {next.name.toUpperCase()}
            </h2>
            <div className="mt-2 font-mono text-[10px] opacity-60 tracking-widest uppercase">
              {next.flag} {next.circuit} . {next.lengthKm.toFixed(3)} km . {next.laps} Laps .{" "}
              {new Date(next.date).toDateString()}
            </div>
            {nextRacePrediction && (
              <Link to={`/predictions/${nextRacePrediction.slug}`} className="btn-stamp mt-4 inline-block text-xs">
                View Prediction →
              </Link>
            )}
          </div>
          <div className="grid grid-cols-4 gap-2 shrink-0">
            {([
              { label: "Days", value: countdown.d },
              { label: "Hrs", value: countdown.h },
              { label: "Min", value: countdown.m },
              { label: "Sec", value: countdown.s },
            ] as const).map((item) => (
              <div key={item.label} className="bg-black/60 border border-white/10 px-3 py-3 md:px-4 md:py-4 text-center">
                <div className="font-mono text-2xl md:text-3xl text-[var(--cyan)] tabular-nums">
                  {String(item.value).padStart(2, "0")}
                </div>
                <div className="font-mono text-[8px] tracking-[0.2em] uppercase opacity-50 mt-1">
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Checker />

      {/* ── Published Predictions ── */}
      {predictions.length > 0 && (
        <section className="px-4 md:px-8 py-8">
          <div className="text-tag mb-2">Model Forecasts</div>
          <h2 className="font-poster text-4xl md:text-5xl mb-5 tracking-wider">PUBLISHED PREDICTIONS</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {predictions.map((pred) => {
              const race = siteData.races.find((r) => r.round === pred.round);
              const p1 = pred.podium[0];
              const p1Driver = p1 ? driverByCode(p1.code, siteData.drivers) : null;
              return (
                <Link
                  key={pred.slug}
                  to={`/predictions/${pred.slug}`}
                  className="border border-black/15 p-4 hover:bg-black/5 transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-mono text-[9px] tracking-widest opacity-50 uppercase">
                        R{String(pred.round).padStart(2, "0")} . {race?.country}
                      </div>
                      <div className="font-display font-bold uppercase text-base leading-tight mt-1">
                        {pred.raceName}
                      </div>
                    </div>
                    <div className="bg-[var(--redorange)] text-white px-2 py-1 font-mono text-[8px] tracking-wider uppercase shrink-0">
                      {pred.status}
                    </div>
                  </div>
                  {p1Driver && (
                    <div className="mt-3 flex items-center gap-2" style={{ borderLeft: `3px solid ${p1Driver.color}` }}>
                      <div className="pl-2">
                        <div className="font-mono text-[9px] opacity-50">Predicted P1</div>
                        <div className="font-poster text-xl tracking-wider">{p1Driver.code}</div>
                        <div className="font-mono text-[10px] opacity-60">{p1.confidence.toFixed(1)}% conf.</div>
                      </div>
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <Checker />

      {/* ── Season Calendar ── */}
      <section className="px-4 md:px-8 py-8">
        <div className="text-tag mb-2">2026 Season Calendar</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-5 tracking-wider">THE CIRCUIT TOUR</h2>
        <div className="overflow-x-auto -mx-4 md:-mx-8 px-4 md:px-8 pb-3">
          <div className="flex gap-2 min-w-max">
            {siteData.races.map((race) => {
              const isNext = race.status === "next";
              const isDone = race.status === "completed";
              const isCancelled = race.status === "cancelled";
              const hasPrediction = predictions.some((p) => p.round === race.round);

              return (
                <div
                  key={race.round}
                  className={`w-32 shrink-0 p-3 border ${
                    isNext
                      ? "bg-[var(--redorange)] text-white border-[var(--redorange)]"
                      : isCancelled
                        ? "bg-black/5 text-black/50 border-black/10"
                        : hasPrediction
                          ? "border-[var(--redorange)]/40 bg-[var(--redorange)]/5"
                          : "border-black/15"
                  }`}
                >
                  <div className="font-mono text-[9px] tracking-widest uppercase opacity-60">
                    R{String(race.round).padStart(2, "0")}
                  </div>
                  <div className="text-xl mt-1">{race.flag}</div>
                  <div className="font-display font-bold uppercase text-xs leading-tight mt-1">
                    {race.name}
                  </div>
                  <div className="font-mono text-[9px] mt-1 opacity-60">
                    {new Date(race.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </div>
                  {isDone && race.winner && (
                    <div className="mt-1 text-[10px] font-bold tracking-wider">🏆 {race.winner}</div>
                  )}
                  {isCancelled && (
                    <div className="mt-1 text-[10px] font-bold tracking-wider uppercase opacity-70">Cancelled</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <Checker />

      {/* ── Standings ── */}
      <section className="px-4 md:px-8 py-8">
        <div className="grid md:grid-cols-2 gap-8">
          {/* Drivers */}
          <div>
            <div className="text-tag mb-2">Drivers' Championship</div>
            <h2 className="font-poster text-3xl md:text-4xl mb-4 tracking-wider">PILOTS' TABLE</h2>
            <div>
              {drivers.map((driver, index) => {
                const isHamilton = driver.code === "HAM";
                return (
                  <div
                    key={driver.code}
                    className={`flex items-center gap-3 py-2 border-t border-black/15 ${isHamilton ? "bg-[var(--redorange)]/10" : ""}`}
                    style={{ borderLeft: `3px solid ${driver.color}` }}
                  >
                    <div className="font-mono text-lg w-8 text-right opacity-70 pl-1">{index + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-bold uppercase text-sm leading-tight truncate">
                        {driver.name} {isHamilton && <span className="text-[var(--redorange)]">#44</span>}
                      </div>
                      <div className="text-[10px] uppercase tracking-widest opacity-60">{driver.team}</div>
                    </div>
                    <div className="font-mono text-base tabular-nums">{driver.points}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Constructors */}
          <div>
            <div className="text-tag mb-2">Constructors' Championship</div>
            <h2 className="font-poster text-3xl md:text-4xl mb-4 tracking-wider">TEAMS' TABLE</h2>
            <div>
              {constructors.map((constructor, index) => (
                <div key={constructor.team} className="py-3 border-t border-black/15">
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-base opacity-70">{index + 1}</span>
                      <span className="font-display font-bold uppercase text-sm">{constructor.team}</span>
                    </div>
                    <span className="font-mono text-sm tabular-nums">{constructor.points}</span>
                  </div>
                  <div className="h-1.5 mt-1.5 bg-black/10">
                    <div
                      className="h-full bar-anim"
                      style={{
                        background: constructor.color,
                        width: `${(constructor.points / maxConstructorPoints) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </PageShell>
  );
}

function SpeedLines() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {[20, 45, 70, 85].map((top, index) => (
        <div
          key={index}
          className="speed-line"
          style={{ top: `${top}%`, width: "30%", animationDelay: `${index * 0.7}s` }}
        />
      ))}
    </div>
  );
}
