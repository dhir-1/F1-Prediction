import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { BlossomBranch } from "@/components/BlossomBranch";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { constructorStandings, standings, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard - Dhir's Pit Wall" },
      { name: "description", content: "2026 F1 season dashboard: next race, standings, and calendar." },
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
  const maxConstructorPoints = Math.max(...constructors.map((constructor) => constructor.points));

  return (
    <PageShell>
      <section className="relative px-6 md:px-16 pt-20 pb-16 overflow-hidden">
        <BlossomBranch className="absolute top-0 left-0 w-64 md:w-96 opacity-60" />
        <BlossomBranch className="absolute top-0 right-0 w-64 md:w-96 opacity-60" flip />
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="text-tag mb-4">Miami Forecast . 2026 Season Build</div>
          <h1 className="font-poster italic leading-[0.85] text-[15vw] md:text-[10rem]">
            <span className="block">DHIR'S</span>
            <span className="block text-[var(--redorange)]">PIT WALL</span>
          </h1>
          <div className="mx-auto w-32 h-[2px] bg-[var(--redorange)] my-6" />
          <p className="font-display uppercase tracking-[0.4em] text-sm opacity-80">
            2026 Formula One Predictions
          </p>
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16 relative overflow-hidden">
        <SpeedLines />
        <div className="text-tag mb-3">Round {String(next.round).padStart(2, "0")} . Next Up</div>
        <h2 className="font-poster text-6xl md:text-8xl tracking-wider leading-none">
          {next.name.toUpperCase()}
        </h2>
        <div className="mt-3 font-mono text-xs opacity-70 tracking-widest uppercase">
          {next.flag} {next.circuit} . {next.lengthKm.toFixed(3)} km . {next.laps} Laps .{" "}
          {new Date(next.date).toDateString()}
        </div>
        <p className="mt-4 max-w-2xl text-sm text-white/70 leading-relaxed">
          The frontend is already wired to your pre-qualifying Miami prediction. Once you add the
          real grid and rerun `backend/scripts/generate_prediction.py`, this same layout can flip
          straight into final forecast mode.
        </p>
        <div className="grid grid-cols-4 gap-2 md:gap-4 mt-10 max-w-2xl">
          {[
            { label: "Days", value: countdown.d },
            { label: "Hours", value: countdown.h },
            { label: "Mins", value: countdown.m },
            { label: "Secs", value: countdown.s },
          ].map((item) => (
            <div key={item.label} className="bg-black/60 border border-white/10 p-4 md:p-6 text-center">
              <div className="font-mono text-3xl md:text-5xl text-[var(--cyan)] tabular-nums">
                {String(item.value).padStart(2, "0")}
              </div>
              <div className="font-mono text-[10px] tracking-[0.3em] uppercase opacity-60 mt-1">
                {item.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">2026 Season Calendar</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">THE CIRCUIT TOUR</h2>
        <div className="overflow-x-auto -mx-6 md:-mx-16 px-6 md:px-16 pb-4">
          <div className="flex gap-3 min-w-max">
            {siteData.races.map((race) => {
              const isNext = race.status === "next";
              const isDone = race.status === "completed";
              const isCancelled = race.status === "cancelled";

              return (
                <div
                  key={race.round}
                  className={`w-44 shrink-0 p-4 border ${
                    isNext
                      ? "bg-[var(--redorange)] text-white border-[var(--redorange)]"
                      : isCancelled
                        ? "bg-black/5 text-black/60 border-black/10"
                        : "border-black/15"
                  }`}
                >
                  <div className="font-mono text-[10px] tracking-widest uppercase opacity-70">
                    R{String(race.round).padStart(2, "0")}
                  </div>
                  <div className="text-3xl mt-1">{race.flag}</div>
                  <div className="font-display font-bold uppercase text-base leading-tight mt-2">
                    {race.name}
                  </div>
                  <div className="font-mono text-[10px] mt-2 opacity-70">
                    {new Date(race.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </div>
                  {isDone && race.winner && (
                    <div className="mt-2 text-[11px] font-bold tracking-wider">Winner . {race.winner}</div>
                  )}
                  {isCancelled && (
                    <div className="mt-2 text-[11px] font-bold tracking-wider uppercase">Cancelled</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <div className="text-tag mb-3">Drivers' Championship</div>
            <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">PILOTS' TABLE</h2>
            <div>
              {drivers.map((driver, index) => {
                const isHamilton = driver.code === "HAM";

                return (
                  <div
                    key={driver.code}
                    className={`flex items-center gap-4 py-3 border-t border-black/15 ${isHamilton ? "bg-[var(--redorange)]/10" : ""}`}
                    style={{ borderLeft: `4px solid ${driver.color}` }}
                  >
                    <div className="font-mono text-2xl w-10 text-right opacity-70 pl-2">{index + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-bold uppercase text-lg leading-tight truncate">
                        {driver.name} {isHamilton && <span className="text-[var(--redorange)]">#44</span>}
                      </div>
                      <div className="text-[11px] uppercase tracking-widest opacity-60">{driver.team}</div>
                    </div>
                    <div className="font-mono text-xl tabular-nums">{driver.points}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <div className="text-tag mb-3">Constructors' Championship</div>
            <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">TEAMS' TABLE</h2>
            <div>
              {constructors.map((constructor, index) => (
                <div key={constructor.team} className="py-4 border-t border-black/15">
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="flex items-baseline gap-3">
                      <span className="font-mono text-xl opacity-70">{index + 1}</span>
                      <span className="font-display font-bold uppercase text-lg">{constructor.team}</span>
                    </div>
                    <span className="font-mono text-lg tabular-nums">{constructor.points}</span>
                  </div>
                  <div className="h-2 mt-2 bg-black/10">
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

      <Checker />

      <section className="bg-[var(--cream-pink)] px-6 md:px-16 py-16 border-l-[6px] border-[var(--rose)]">
        <div className="max-w-3xl">
          <div className="text-[var(--rose)] text-2xl mb-4">MIAMI . MODEL . PIT WALL</div>
          <p className="font-serif italic text-3xl md:text-5xl leading-tight text-[var(--ink)]">
            "Built now for the look, ready later for the final grid."
          </p>
          <div className="mt-6 font-mono text-[11px] tracking-[0.3em] uppercase opacity-60">
            A note from the pit wall
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
