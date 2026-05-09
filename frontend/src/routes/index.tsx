import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { BlossomBranch } from "@/components/BlossomBranch";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { constructorStandings, driverByCode, standings, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/")({
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
  const next = siteData.races.find((race) => race.status === "next") ?? siteData.races[0];
  const countdown = useCountdown(next.date);
  const maxConstructorPoints = Math.max(...constructors.map((constructor) => constructor.points), 1);
  const predictions = siteData.predictions;
  const completedRaces = siteData.races.filter((race) => race.status === "completed");
  const latestCompletedRace = completedRaces[completedRaces.length - 1];
  const latestWinner = latestCompletedRace?.winner
    ? driverByCode(latestCompletedRace.winner, siteData.drivers)
    : null;
  const nextRacePrediction = predictions.find((prediction) => prediction.round === next.round);
  const latestPublishedPrediction = predictions[predictions.length - 1];
  const latestPredictionWinner =
    latestPublishedPrediction?.actualResult?.[0]?.driver ?? latestCompletedRace?.winner ?? null;
  const latestPredictionWinnerDriver = latestPredictionWinner
    ? driverByCode(latestPredictionWinner, siteData.drivers)
    : null;

  return (
    <PageShell>
      <section className="relative px-4 md:px-8 pt-10 pb-8 overflow-hidden">
        <BlossomBranch className="absolute top-0 left-0 w-40 md:w-64 opacity-50" />
        <BlossomBranch className="absolute top-0 right-0 w-40 md:w-64 opacity-50" flip />

        <div className="relative grid gap-10 xl:grid-cols-[minmax(0,1.12fr)_420px] xl:items-end">
          <div>
            <div className="text-tag mb-2">2026 Season . Race Predictions</div>
            <h1 className="font-poster italic leading-[0.85] text-[13vw] md:text-[7.5rem]">
              <span className="block">DHIR'S</span>
              <span className="block text-[var(--redorange)]">PIT WALL</span>
            </h1>
            <p className="font-display uppercase tracking-[0.3em] text-sm opacity-70 mt-4 max-w-2xl">
              Formula One . Machine Learning . Season Tracker
            </p>
          </div>

          <aside className="border border-black/15 bg-black/[0.03]">
            <div className="p-5 border-b border-black/10">
              <div className="text-tag">Season Briefing</div>
              <div className="grid grid-cols-2 gap-5 mt-4">
                <BriefStat label="Completed" value={String(completedRaces.length).padStart(2, "0")} />
                <BriefStat label="Forecasts" value={String(predictions.length).padStart(2, "0")} />
                <BriefStat label="Next Round" value={String(next.round).padStart(2, "0")} />
                <BriefStat label="Current P1" value={drivers[0]?.code ?? "--"} />
              </div>
            </div>

            <div className="p-5">
              <div className="text-tag">Latest Result</div>
              {latestCompletedRace && latestWinner ? (
                <div className="mt-3 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="font-display font-bold uppercase text-sm leading-tight">
                      {latestCompletedRace.name}
                    </div>
                    <div className="mt-2 font-poster text-4xl tracking-wider" style={{ color: latestWinner.color }}>
                      {latestWinner.code}
                    </div>
                    <div className="font-mono text-[10px] tracking-widest uppercase opacity-55 mt-1">
                      {latestWinner.name} . {latestWinner.team}
                    </div>
                  </div>
                  {latestWinner.headshot ? (
                    <img
                      src={latestWinner.headshot}
                      alt={latestWinner.name}
                      className="h-24 w-20 object-contain object-bottom grayscale opacity-75"
                    />
                  ) : null}
                </div>
              ) : (
                <div className="mt-3 font-mono text-xs uppercase tracking-widest opacity-50">
                  Waiting for the first classified finish.
                </div>
              )}
            </div>
          </aside>
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-8 relative overflow-hidden">
        <SpeedLines />
        <div className="relative grid gap-8 xl:grid-cols-[minmax(0,1.18fr)_430px] xl:items-end">
          <div>
            <div className="text-tag mb-1">Round {String(next.round).padStart(2, "0")} . Next Up</div>
            <h2 className="font-poster text-5xl md:text-7xl tracking-wider leading-none">
              {next.name.toUpperCase()}
            </h2>
            <div className="mt-2 font-mono text-[10px] opacity-60 tracking-widest uppercase">
              {next.flag} {next.circuit} . {next.lengthKm.toFixed(3)} km . {next.laps} laps .{" "}
              {new Date(next.date).toDateString()}
            </div>
            {nextRacePrediction ? (
              <Link to={`/predictions/${nextRacePrediction.slug}`} className="btn-stamp mt-4 inline-block text-xs">
                View Prediction
              </Link>
            ) : (
              <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.24em] text-white/55">
                Prediction page not published yet.
              </div>
            )}
          </div>

          <div className="grid gap-4">
            <div className="grid grid-cols-4 gap-2">
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

            <div className="border border-white/10 bg-black/30 p-4">
              <div className="text-tag text-white/70">Forecast Status</div>
              {nextRacePrediction ? (
                <>
                  <div className="mt-3 flex items-start justify-between gap-3">
                    <div>
                      <div className="font-display font-bold uppercase text-sm">{nextRacePrediction.raceName}</div>
                      <div className="font-mono text-[10px] tracking-widest uppercase opacity-50 mt-1">
                        {nextRacePrediction.status} . {nextRacePrediction.modelUsed}
                      </div>
                    </div>
                    <div className="bg-[var(--redorange)] px-2 py-1 font-mono text-[8px] uppercase tracking-widest">
                      Live
                    </div>
                  </div>
                  {nextRacePrediction.podium[0] && (
                    <div className="mt-4 border-t border-white/10 pt-4">
                      <div className="font-mono text-[10px] uppercase tracking-widest opacity-50">Projected Pole Story</div>
                      <div className="mt-2 flex items-end justify-between gap-3">
                        <div>
                          <div className="font-poster text-4xl tracking-wider">
                            {nextRacePrediction.podium[0].code}
                          </div>
                          <div className="font-display font-bold uppercase text-xs mt-1">
                            {driverByCode(nextRacePrediction.podium[0].code, siteData.drivers).name}
                          </div>
                        </div>
                        <div className="font-mono text-sm text-[var(--cyan)]">
                          {nextRacePrediction.podium[0].confidence.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="mt-3 text-sm text-white/75 leading-relaxed">
                  The next round is already on the board, so the layout is ready for the forecast as soon as you publish the next JSON file.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <Checker />

      {predictions.length > 0 && (
        <section className="px-4 md:px-8 py-8">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1.18fr)_340px]">
            <div>
              <div className="text-tag mb-2">Model Forecasts</div>
              <h2 className="font-poster text-4xl md:text-5xl mb-5 tracking-wider">PUBLISHED PREDICTIONS</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {predictions.map((prediction) => {
                  const race = siteData.races.find((item) => item.round === prediction.round);
                  const p1 = prediction.podium[0];
                  const p1Driver = p1 ? driverByCode(p1.code, siteData.drivers) : null;
                  return (
                    <Link
                      key={prediction.slug}
                      to={`/predictions/${prediction.slug}`}
                      className="border border-black/15 p-4 hover:bg-black/5 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-mono text-[9px] tracking-widest opacity-50 uppercase">
                            R{String(prediction.round).padStart(2, "0")} . {race?.country}
                          </div>
                          <div className="font-display font-bold uppercase text-base leading-tight mt-1">
                            {prediction.raceName}
                          </div>
                        </div>
                        <div className="bg-[var(--redorange)] text-white px-2 py-1 font-mono text-[8px] tracking-wider uppercase shrink-0">
                          {prediction.status}
                        </div>
                      </div>

                      {p1Driver && (
                        <div className="mt-3 flex items-center gap-3" style={{ borderLeft: `3px solid ${p1Driver.color}` }}>
                          <div className="pl-2 min-w-0">
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
            </div>

            <aside className="border border-black/15 bg-black/[0.03] p-5">
              <div className="text-tag">Result Watch</div>
              {latestPredictionWinnerDriver && latestPublishedPrediction ? (
                <>
                  <div className="mt-3 font-display font-bold uppercase text-sm">{latestPublishedPrediction.raceName}</div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <div>
                      <div className="font-poster text-5xl tracking-wider" style={{ color: latestPredictionWinnerDriver.color }}>
                        {latestPredictionWinnerDriver.code}
                      </div>
                      <div className="font-mono text-[10px] tracking-widest uppercase opacity-55 mt-1">
                        {latestPredictionWinnerDriver.name}
                      </div>
                    </div>
                    {latestPredictionWinnerDriver.headshot ? (
                      <img
                        src={latestPredictionWinnerDriver.headshot}
                        alt={latestPredictionWinnerDriver.name}
                        className="h-24 w-20 object-contain object-bottom grayscale opacity-75"
                      />
                    ) : null}
                  </div>

                  <div className="mt-4 border-t border-black/10 pt-4 text-sm leading-relaxed">
                    The latest published page now carries both the forecast and the post-race check, so the archive and prediction board stay in sync.
                  </div>

                  <div className="mt-4">
                    <Link to="/history" className="btn-stamp inline-block text-xs">
                      Open Archive
                    </Link>
                  </div>
                </>
              ) : (
                <div className="mt-3 text-sm leading-relaxed opacity-70">
                  Once the first result is logged, this rail becomes the bridge between published forecasts and the season archive.
                </div>
              )}
            </aside>
          </div>
        </section>
      )}

      <Checker />

      <section className="px-4 md:px-8 py-8">
        <div className="text-tag mb-2">2026 Season Calendar</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-5 tracking-wider">THE CIRCUIT TOUR</h2>
        <div className="overflow-x-auto -mx-4 md:-mx-8 px-4 md:px-8 pb-3">
          <div className="flex gap-2 min-w-max">
            {siteData.races.map((race) => {
              const isNext = race.status === "next";
              const isDone = race.status === "completed";
              const isCancelled = race.status === "cancelled";
              const hasPrediction = predictions.some((prediction) => prediction.round === race.round);

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
                    <div className="mt-1 text-[10px] font-bold tracking-wider">{race.winner} won</div>
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

      <section className="px-4 md:px-8 py-8">
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <div className="text-tag mb-2">Drivers' Championship</div>
            <h2 className="font-poster text-3xl md:text-4xl mb-4 tracking-wider">PILOTS' TABLE</h2>
            <div>
              {drivers.map((driver, index) => {
                return (
                  <div
                    key={driver.code}
                    className="flex items-center gap-3 py-2 border-t border-black/15"
                    style={{ borderLeft: `3px solid ${driver.color}` }}
                  >
                    <div className="font-mono text-lg w-8 text-right opacity-70 pl-1">{index + 1}</div>
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-bold uppercase text-sm leading-tight truncate">
                        {driver.name}
                        {driver.number ? (
                          <span className="text-[var(--redorange)] ml-2 font-mono text-xs">#{driver.number}</span>
                        ) : null}
                      </div>
                      <div className="text-[10px] uppercase tracking-widest opacity-60">{driver.team}</div>
                    </div>
                    <div className="font-mono text-base tabular-nums">{driver.points}</div>
                  </div>
                );
              })}
            </div>
          </div>

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

function BriefStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-tag">{label}</div>
      <div className="font-poster text-3xl tracking-wider mt-2">{value}</div>
    </div>
  );
}
