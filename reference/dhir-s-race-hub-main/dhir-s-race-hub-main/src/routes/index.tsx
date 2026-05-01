import { createFileRoute } from "@tanstack/react-router";
import { PageShell } from "@/components/PageShell";
import { Checker } from "@/components/Checker";
import { BlossomBranch } from "@/components/BlossomBranch";
import { DRIVERS, RACES, standings, constructorStandings, driverByCode } from "@/lib/data";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Dhir's Pit Wall" },
      { name: "description", content: "2026 F1 season dashboard: next race, standings, calendar." },
      { property: "og:title", content: "Dashboard — Dhir's Pit Wall" },
      { property: "og:description", content: "2026 F1 season dashboard." },
    ],
  }),
  component: Index,
});

function useCountdown(targetIso: string) {
  const [t, setT] = useState({ d: 0, h: 0, m: 0, s: 0 });
  useEffect(() => {
    const target = new Date(targetIso).getTime();
    const tick = () => {
      const diff = Math.max(0, target - Date.now());
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff / 3600000) % 24);
      const m = Math.floor((diff / 60000) % 60);
      const s = Math.floor((diff / 1000) % 60);
      setT({ d, h, m, s });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [targetIso]);
  return t;
}

function Index() {
  const drivers = standings();
  const constructors = constructorStandings();
  const next = RACES.find((r) => r.status === "next")!;
  const c = useCountdown(next.date);
  const maxC = Math.max(...constructors.map((x) => x.points));

  return (
    <PageShell>
      {/* HERO */}
      <section className="relative px-6 md:px-16 pt-20 pb-16 overflow-hidden">
        <BlossomBranch className="absolute top-0 left-0 w-64 md:w-96 opacity-60" />
        <BlossomBranch className="absolute top-0 right-0 w-64 md:w-96 opacity-60" flip />
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="text-tag mb-4">⭐ Lewis Hamilton · Ferrari</div>
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

      {/* NEXT RACE */}
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16 relative overflow-hidden">
        <SpeedLines />
        <div className="text-tag mb-3">Round 0{next.round} · Next Up</div>
        <h2 className="font-poster text-6xl md:text-8xl tracking-wider leading-none">
          {next.name.toUpperCase()}
        </h2>
        <div className="mt-3 font-mono text-xs opacity-70 tracking-widest uppercase">
          {next.flag} {next.circuit} · {next.lengthKm.toFixed(3)} km · {next.laps} Laps · {new Date(next.date).toDateString()}
        </div>
        <div className="grid grid-cols-4 gap-2 md:gap-4 mt-10 max-w-2xl">
          {[
            { l: "Days", v: c.d },
            { l: "Hours", v: c.h },
            { l: "Mins", v: c.m },
            { l: "Secs", v: c.s },
          ].map((x) => (
            <div key={x.l} className="bg-black/60 border border-white/10 p-4 md:p-6 text-center">
              <div className="font-mono text-3xl md:text-5xl text-[var(--cyan)] tabular-nums">
                {String(x.v).padStart(2, "0")}
              </div>
              <div className="font-mono text-[10px] tracking-[0.3em] uppercase opacity-60 mt-1">{x.l}</div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      {/* CALENDAR */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">2026 Season Calendar</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">THE CIRCUIT TOUR</h2>
        <div className="overflow-x-auto -mx-6 md:-mx-16 px-6 md:px-16 pb-4">
          <div className="flex gap-3 min-w-max">
            {RACES.map((r) => {
              const isNext = r.status === "next";
              const isDone = r.status === "completed";
              return (
                <div
                  key={r.round}
                  className={`w-44 shrink-0 p-4 border ${isNext ? "bg-[var(--redorange)] text-white border-[var(--redorange)]" : "border-black/15"}`}
                >
                  <div className="font-mono text-[10px] tracking-widest uppercase opacity-70">
                    R{String(r.round).padStart(2, "0")}
                  </div>
                  <div className="text-3xl mt-1">{r.flag}</div>
                  <div className="font-display font-bold uppercase text-base leading-tight mt-2">
                    {r.name}
                  </div>
                  <div className="font-mono text-[10px] mt-2 opacity-70">
                    {new Date(r.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </div>
                  {isDone && r.winner && (
                    <div className="mt-2 text-[11px] font-bold tracking-wider">
                      ★ {r.winner}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <Checker />

      {/* DRIVER STANDINGS */}
      <section className="px-6 md:px-16 py-16">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <div className="text-tag mb-3">Drivers' Championship</div>
            <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">PILOTS' TABLE</h2>
            <div>
              {drivers.map((d, i) => {
                const isHam = d.code === "HAM";
                return (
                  <div
                    key={d.code}
                    className={`flex items-center gap-4 py-3 border-t border-black/15 ${isHam ? "bg-[var(--redorange)]/10" : ""}`}
                    style={{ borderLeft: `4px solid ${d.color}` }}
                  >
                    <div className="font-mono text-2xl w-10 text-right opacity-70 pl-2">{i + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-bold uppercase text-lg leading-tight truncate">
                        {d.name} {isHam && <span className="text-[var(--redorange)]">⭐</span>}
                      </div>
                      <div className="text-[11px] uppercase tracking-widest opacity-60">{d.team}</div>
                    </div>
                    <div className="font-mono text-xl tabular-nums">{d.points}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <div className="text-tag mb-3">Constructors' Championship</div>
            <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">TEAMS' TABLE</h2>
            <div>
              {constructors.map((t, i) => (
                <div key={t.team} className="py-4 border-t border-black/15">
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="flex items-baseline gap-3">
                      <span className="font-mono text-xl opacity-70">{i + 1}</span>
                      <span className="font-display font-bold uppercase text-lg">{t.team}</span>
                    </div>
                    <span className="font-mono text-lg tabular-nums">{t.points}</span>
                  </div>
                  <div className="h-2 mt-2 bg-black/10">
                    <div
                      className="h-full bar-anim"
                      style={{ background: t.color, width: `${(t.points / maxC) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <Checker />

      {/* BLOSSOM BANNER */}
      <section className="bg-[var(--cream-pink)] px-6 md:px-16 py-16 border-l-[6px] border-[var(--rose)]">
        <div className="max-w-3xl">
          <div className="text-[var(--rose)] text-2xl mb-4">🌸 🌸 🌸</div>
          <p className="font-serif italic text-3xl md:text-5xl leading-tight text-[var(--ink)]">
            "Where speed meets serenity — Dhir's 2026 season in full bloom."
          </p>
          <div className="mt-6 font-mono text-[11px] tracking-[0.3em] uppercase opacity-60">
            — A note from the pit wall
          </div>
        </div>
      </section>
    </PageShell>
  );
}

function SpeedLines() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {[20, 45, 70, 85].map((top, i) => (
        <div
          key={i}
          className="speed-line"
          style={{ top: `${top}%`, width: "30%", animationDelay: `${i * 0.7}s` }}
        />
      ))}
    </div>
  );
}
