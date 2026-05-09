import React from "react";
import { Link, createFileRoute } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { type Driver, type Race, type RacePrediction, driverByCode, useSiteData } from "@/lib/data";

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
  const { races, drivers, predictions } = useSiteData();
  const completed = races.filter((race) => race.status === "completed");
  const cancelled = races.filter((race) => race.status === "cancelled");
  const upcomingCount = races.length - completed.length - cancelled.length;
  const progress = races.length > 0 ? (completed.length / races.length) * 100 : 0;
  const latestCompleted = completed[completed.length - 1];
  const latestWinner = latestCompleted?.winner ? driverByCode(latestCompleted.winner, drivers) : null;
  const predictionsByRound = new Map(predictions.map((prediction) => [prediction.round, prediction]));

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
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.5fr)_360px] xl:items-end">
          <div>
            <div className="text-tag mb-2">2026 Season Archive</div>
            <h1 className="font-poster text-6xl md:text-[8rem] leading-[0.85] tracking-wider">
              RACE <span className="text-[var(--redorange)] italic">HISTORY</span>
            </h1>
            <p className="mt-4 font-serif italic text-lg md:text-xl max-w-3xl leading-relaxed">
              {completed.length} rounds are in the books, {cancelled.length} weekends were cancelled, and {upcomingCount} races remain on the calendar.
            </p>
          </div>

          <div className="border border-black/15 bg-black/[0.03]">
            <div className="grid grid-cols-2 gap-x-6 gap-y-4 p-5">
              <SummaryStat label="Completed" value={String(completed.length).padStart(2, "0")} />
              <SummaryStat label="Forecasts Logged" value={String(predictions.length).padStart(2, "0")} />
              <SummaryStat label="Next Round" value={String((completed.length + 1)).padStart(2, "0")} />
              <SummaryStat label="Latest Winner" value={latestWinner?.code ?? "--"} />
            </div>
            {latestCompleted && latestWinner && (
              <div className="border-t border-black/10 px-5 py-4">
                <div className="text-tag">Most Recent Result</div>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <div>
                    <div className="font-display font-bold uppercase text-sm">{latestCompleted.name}</div>
                    <div className="font-mono text-[10px] tracking-widest opacity-55 mt-1">
                      {latestWinner.name} . {latestWinner.team}
                    </div>
                  </div>
                  <div className="font-poster text-4xl tracking-wider" style={{ color: latestWinner.color }}>
                    {latestWinner.code}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

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
          <RaceSection race={race} drivers={drivers} prediction={predictionsByRound.get(race.round)} />
        </div>
      ))}
    </PageShell>
  );
}

function RaceSection({
  race,
  drivers,
  prediction,
}: {
  race: Race;
  drivers: Driver[];
  prediction?: RacePrediction;
}) {
  const [winnerImageError, setWinnerImageError] = React.useState(false);
  const [headshotError, setHeadshotError] = React.useState(false);
  const winner = race.winner ? driverByCode(race.winner, drivers) : null;
  const podiumDrivers = race.podium?.map((code) => driverByCode(code, drivers)) ?? [];
  const heroBackground = winner
    ? `linear-gradient(135deg, color-mix(in srgb, ${winner.color} 24%, black), black 78%)`
    : "linear-gradient(135deg, rgba(0,0,0,0.85), rgba(0,0,0,1))";
  const showWinnerImage = Boolean(race.winnerImage && !winnerImageError);
  const showHeadshot = Boolean(!showWinnerImage && winner?.headshot && !headshotError);

  return (
    <section className="px-4 md:px-8 py-10">
      <div className="text-tag mb-2">
        Round {String(race.round).padStart(2, "0")} . {race.flag} {race.country}
      </div>
      <h2 className="font-poster text-4xl md:text-6xl leading-[0.9] tracking-wider mb-5">
        {race.name.toUpperCase()}
      </h2>

      <div
        className="relative overflow-hidden border border-black/10 bg-[var(--charcoal)] text-[var(--cream)]"
        style={{ background: heroBackground }}
      >
        {showWinnerImage && (
          <>
            <img
              src={race.winnerImage}
              alt={`${race.name} winner`}
              onError={() => setWinnerImageError(true)}
              className="absolute inset-0 h-full w-full object-cover opacity-50 mix-blend-luminosity"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/45 to-black/70" />
          </>
        )}

        {showHeadshot && winner?.headshot && (
          <img
            src={winner.headshot}
            alt={winner.name}
            onError={() => setHeadshotError(true)}
            className="absolute right-0 bottom-0 h-full max-w-[48%] object-contain object-right-bottom opacity-35 grayscale"
          />
        )}

        {!showWinnerImage && (
          <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.04)_35%,transparent_65%)]" />
        )}

        {!showWinnerImage && !showHeadshot && winner && (
          <div className="absolute right-4 bottom-0 font-poster text-[7rem] md:text-[12rem] leading-none text-white/[0.06] pointer-events-none">
            {winner.code}
          </div>
        )}

        <div className="relative grid gap-0 xl:grid-cols-[minmax(0,1.3fr)_320px]">
          <div className="px-5 md:px-8 py-8 md:py-10 min-h-[340px] md:min-h-[420px] flex flex-col justify-between">
            <div>
              <div className="text-tag text-white/70">Winner Spotlight</div>
              {winner ? (
                <>
                  <h3 className="font-poster text-5xl md:text-[6.5rem] leading-[0.88] tracking-wider mt-3">
                    {winner.name.toUpperCase()}
                  </h3>
                  <div className="mt-4 flex flex-wrap items-center gap-3 text-sm md:text-base">
                    <span
                      className="inline-flex items-center px-3 py-1 font-display font-bold uppercase tracking-[0.18em] text-xs text-white"
                      style={{ backgroundColor: winner.color }}
                    >
                      {winner.code} Wins
                    </span>
                    <span className="font-display uppercase tracking-[0.12em] text-white/80">
                      {winner.team}
                      {winner.number ? ` . #${winner.number}` : ""}
                    </span>
                  </div>
                </>
              ) : (
                <h3 className="font-poster text-5xl md:text-[6rem] leading-[0.88] tracking-wider mt-3">
                  RESULT LOGGING
                </h3>
              )}
            </div>

            <div className="max-w-2xl">
              <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-white/55">
                {race.circuit}
              </div>
              <div className="mt-3 h-px w-full bg-white/12" />
              <p className="mt-3 text-sm md:text-base text-white/78 leading-relaxed max-w-xl">
                {prediction
                  ? "Published forecast and archived result are now tied together here, so every finished weekend keeps both the call and the outcome in one place."
                  : "Completed race data is archived here automatically, and local winner photos can still be dropped in later without changing the page structure."}
              </p>
            </div>
          </div>

          <aside className="border-t border-white/10 xl:border-t-0 xl:border-l xl:border-white/10 bg-black/28 px-5 py-6 md:px-6 md:py-8">
            <div className="text-tag text-white/70">Podium Board</div>
            <div className="mt-4 space-y-4">
              {podiumDrivers.map((driver, index) => (
                <div key={`${race.round}-${driver.code}`} className="border-b border-white/10 pb-4 last:border-b-0 last:pb-0">
                  <div className="font-mono text-[10px] tracking-widest uppercase text-white/45">P{index + 1}</div>
                  <div className="mt-1 flex items-end justify-between gap-3">
                    <div>
                      <div className="font-poster text-3xl tracking-wider" style={{ color: driver.color }}>
                        {driver.code}
                      </div>
                      <div className="font-display font-bold uppercase text-xs mt-1">{driver.name}</div>
                      <div className="font-mono text-[10px] tracking-widest uppercase text-white/45 mt-1">
                        {driver.team}
                      </div>
                    </div>
                    {driver.number && <div className="font-mono text-sm text-white/45">#{driver.number}</div>}
                  </div>
                </div>
              ))}
            </div>

            {prediction && (
              <div className="mt-6 border-t border-white/10 pt-5">
                <div className="text-tag text-white/70">Forecast Archive</div>
                <Link to={`/predictions/${prediction.slug}`} className="btn-stamp mt-3 inline-block text-xs">
                  View Prediction
                </Link>
              </div>
            )}
          </aside>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mt-6 border-t border-black/10 pt-4">
        <MetaBlock
          label="Date"
          value={new Date(race.date).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        />
        <MetaBlock label="Laps" value={String(race.laps)} />
        <MetaBlock label="Length" value={`${race.lengthKm.toFixed(3)} km`} />
        <MetaBlock label="Winner" value={winner?.code ?? "--"} />
        <MetaBlock label="Forecast" value={prediction?.status ?? "No page"} />
      </div>
    </section>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-tag">{label}</div>
      <div className="font-poster text-3xl md:text-4xl mt-2 tracking-wider">{value}</div>
    </div>
  );
}

function MetaBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-black/15 pt-2">
      <div className="text-tag">{label}</div>
      <div className="font-mono text-lg md:text-xl mt-1 break-words">{value}</div>
    </div>
  );
}
