import { createFileRoute, notFound } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { driverByCode, getPredictionBySlug, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/predictions/$slug")({
  loader: ({ params }) => {
    return { slug: params.slug };
  },
  component: PredictionDetailPage,
});

function PredictionDetailPage() {
  const { slug } = Route.useLoaderData();
  const siteData = useSiteData();
  const prediction = getPredictionBySlug(slug, siteData.predictions);

  if (!prediction) {
    throw notFound();
  }

  const race = siteData.races.find((r) => r.round === prediction.round);
  const {
    podium,
    grid,
    features,
    metrics,
    modelUsed,
    status,
    trainingData,
    limitations,
    qualifyingDone,
    actualResult,
    pitWallNotes,
  } = prediction;
  const actualPodium =
    actualResult && actualResult.length > 0
      ? actualResult
      : race?.podium?.map((driver, index) => ({ pos: index + 1, driver })) ?? [];
  const exactHits = actualPodium.filter((actual) =>
    podium.some((predicted) => predicted.pos === actual.pos && predicted.code === actual.driver),
  ).length;
  const podiumHits = podium.filter((predicted) =>
    actualPodium.some((actual) => actual.driver === predicted.code),
  ).length;
  const winnerHit =
    actualPodium.length > 0 && podium.length > 0 && actualPodium[0]?.driver === podium[0]?.code;
  const projectedWinner = podium[0] ? driverByCode(podium[0].code, siteData.drivers) : null;
  const actualWinner = actualPodium[0] ? driverByCode(actualPodium[0].driver, siteData.drivers) : null;

  return (
    <PageShell>
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-10 relative overflow-hidden">
        <div className="text-tag mb-2">
          Round {String(prediction.round).padStart(2, "0")} . {race?.country ?? "Unknown"}
        </div>
        <h1 className="font-poster leading-[0.85] text-[12vw] md:text-[8rem] tracking-wider uppercase">
          <span className="block">{prediction.raceName.replace(" Grand Prix", "")} GP</span>
          <span className="block italic text-[var(--redorange)]">PREDICTED.</span>
        </h1>
        <div className="mt-4 inline-block bg-[var(--redorange)] text-white px-4 py-1.5 font-display font-bold tracking-[0.2em] uppercase text-xs">
          {status}
        </div>
        <div className="mt-4 font-mono text-[10px] opacity-70 tracking-widest uppercase">
          {race?.circuit} . {race?.laps} Laps . {race?.lengthKm.toFixed(3)} km
        </div>
        {!qualifyingDone && (
          <p className="mt-4 max-w-2xl text-xs text-white/70 leading-relaxed">
            Grid positions are still estimated from 2026 qualifying form. This page is set up to
            refresh cleanly once you rerun `backend/scripts/generate_prediction.py` after qualifying.
          </p>
        )}
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Predicted Podium</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">THE TOP THREE</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
          {podium.map((pick) => {
            const driver = driverByCode(pick.code, siteData.drivers);
            const tall = pick.pos === 1;
            const orderClass =
              pick.pos === 1 ? "order-1 sm:order-2" : pick.pos === 2 ? "order-2 sm:order-1" : "order-3";

            return (
              <div
                key={pick.code}
                className={`border-l border-r border-black/15 px-4 ${orderClass} ${tall ? "pb-8" : "pb-4"}`}
                style={{ borderLeft: `3px solid ${driver.color}` }}
              >
                <div className="font-poster text-3xl md:text-4xl tracking-wider">P{pick.pos}</div>
                <div
                  className={`font-mono font-bold ${tall ? "text-6xl md:text-8xl" : "text-5xl md:text-6xl"} leading-none mt-2`}
                >
                  {driver.code}
                </div>
                <div className="font-display font-bold uppercase mt-2 text-sm">{driver.name}</div>
                <div className="text-[10px] uppercase tracking-widest opacity-60">{driver.team}</div>
                <div className="mt-2 text-[var(--redorange)] font-mono text-xs font-bold">
                  {pick.confidence.toFixed(1)}% conf.
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {actualPodium.length > 0 && (
        <>
          <Checker />
          <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-10">
            <div className="text-tag mb-2">Post Race</div>
            <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">PREDICTED VS ACTUAL</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
              {[
                { label: "Exact Podium Slots", value: `${exactHits}/${actualPodium.length}` },
                { label: "Drivers On Podium", value: `${podiumHits}/${actualPodium.length}` },
                { label: "Winner Call", value: winnerHit ? "Hit" : "Miss" },
              ].map((item) => (
                <div key={item.label} className="border border-white/10 p-4">
                  <div className="text-tag">{item.label}</div>
                  <div className="font-mono text-2xl md:text-3xl mt-2 uppercase">{item.value}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {actualPodium.map((actual) => {
                const predictedDriver = podium.find((p) => p.pos === actual.pos);
                const correct = predictedDriver?.code === actual.driver;
                const actualDriver = driverByCode(actual.driver, siteData.drivers);
                const predictedDriverData = predictedDriver
                  ? driverByCode(predictedDriver.code, siteData.drivers)
                  : null;

                return (
                  <div
                    key={actual.pos}
                    className="border border-white/10 p-4"
                    style={{ borderLeft: `3px solid ${correct ? "#00ff87" : "var(--redorange)"}` }}
                  >
                    <div className="font-poster text-2xl tracking-wider mb-3">P{actual.pos}</div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono uppercase opacity-50 w-20">Actual</span>
                      <span className="font-mono font-bold text-lg">{actualDriver.code}</span>
                      <span className="text-lg">{correct ? "OK" : "X"}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono uppercase opacity-50 w-20">Predicted</span>
                      <span
                        className="font-mono text-sm opacity-70"
                        style={{ color: correct ? "#00ff87" : "var(--redorange)" }}
                      >
                        {predictedDriverData?.code ?? "-"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-6 font-mono text-xs opacity-50 uppercase tracking-widest">
              Completed race review locked against the published forecast.
            </div>
          </section>
        </>
      )}

      {(pitWallNotes?.length ?? 0) > 0 && (
        <>
          <Checker />
          <section className="px-4 md:px-8 py-10">
            <div className="grid gap-8 xl:grid-cols-[minmax(0,1.22fr)_340px] xl:items-start">
              <div>
                <div className="text-tag mb-2">Editorial Notes</div>
                <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">PIT WALL NOTES</h2>
                <div className="grid gap-3">
                  {pitWallNotes?.map((note, index) => (
                    <div
                      key={`${prediction.slug}-note-${index}`}
                      className="border border-black/15 p-4 bg-[var(--cream)]"
                    >
                      <div className="font-mono text-[10px] tracking-widest uppercase text-[var(--redorange)] mb-2">
                        Note {String(index + 1).padStart(2, "0")}
                      </div>
                      <p className="text-sm leading-relaxed">{note}</p>
                    </div>
                  ))}
                </div>
              </div>

              <aside className="border border-black/15 bg-black/[0.03] p-5">
                <div className="text-tag">Review Board</div>
                <div className="mt-4 space-y-4">
                  <div className="border-b border-black/10 pb-4">
                    <div className="font-mono text-[10px] uppercase tracking-widest opacity-50">
                      Published Winner Call
                    </div>
                    <div className="mt-2 font-poster text-4xl tracking-wider">
                      {projectedWinner?.code ?? "--"}
                    </div>
                    <div className="font-display font-bold uppercase text-xs mt-1">
                      {projectedWinner?.name ?? "Awaiting forecast"}
                    </div>
                  </div>

                  <div className="border-b border-black/10 pb-4">
                    <div className="font-mono text-[10px] uppercase tracking-widest opacity-50">
                      Actual Winner
                    </div>
                    <div className="mt-2 font-poster text-4xl tracking-wider">
                      {actualWinner?.code ?? "--"}
                    </div>
                    <div className="font-display font-bold uppercase text-xs mt-1">
                      {actualWinner?.name ?? "Result pending"}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="border border-black/10 p-3">
                      <div className="font-mono text-[9px] uppercase tracking-widest opacity-50">Exact Slots</div>
                      <div className="font-poster text-3xl mt-2">{`${exactHits}/${actualPodium.length || 3}`}</div>
                    </div>
                    <div className="border border-black/10 p-3">
                      <div className="font-mono text-[9px] uppercase tracking-widest opacity-50">Winner Call</div>
                      <div className="font-poster text-3xl mt-2">{winnerHit ? "HIT" : actualPodium.length ? "MISS" : "--"}</div>
                    </div>
                  </div>

                  <div className="border-t border-black/10 pt-4 text-xs leading-relaxed opacity-75">
                    Model: <span className="font-mono">{modelUsed}</span>
                    <br />
                    Status: <span className="font-mono">{status}</span>
                    <br />
                    Training rows: <span className="font-mono">{trainingData.rows}</span>
                  </div>
                </div>
              </aside>
            </div>
          </section>
        </>
      )}

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Predicted Order</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">FULL GRID FORECAST</h2>
        <div>
          {grid.map((entry) => {
            const driver = driverByCode(entry.code, siteData.drivers);

            return (
              <div
                key={entry.code}
                className="grid grid-cols-[40px_60px_1fr_120px] md:grid-cols-[50px_80px_1fr_200px] items-center gap-2 py-2 border-t border-black/15"
                style={{ borderLeft: `3px solid ${driver.color}` }}
              >
                <div className="font-mono text-sm md:text-base pl-2 opacity-70">P{entry.predictedPosition}</div>
                <div className="font-mono font-bold text-base md:text-xl">{driver.code}</div>
                <div className="min-w-0">
                  <div className="font-display font-bold uppercase text-xs md:text-sm truncate">{driver.name}</div>
                  <div className="text-[9px] uppercase tracking-widest opacity-60">{driver.team}</div>
                  <div className="text-[9px] uppercase tracking-widest opacity-40 mt-0.5">
                    Grid P{entry.gridPosition} . {entry.gridSource}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-black/10">
                    <div
                      className="h-full bar-anim"
                      style={{ background: "var(--redorange)", width: `${entry.probability}%` }}
                    />
                  </div>
                  <div className="font-mono text-[10px] w-10 text-right tabular-nums">
                    {entry.probability.toFixed(1)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Model Internals</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">FEATURE WEIGHT</h2>
        <div className="space-y-2">
          {features.map((feature, index) => (
            <div key={feature.key} className="flex items-center gap-3">
              <div className="font-mono text-[9px] tracking-widest uppercase w-32 md:w-48 opacity-80 truncate">
                {String(index + 1).padStart(2, "0")} . {feature.name}
              </div>
              <div className="flex-1 h-4 bg-white/5 relative">
                <div
                  className="h-full bar-anim"
                  style={{
                    width: `${feature.weight}%`,
                    background: index === 0 ? "var(--redorange)" : "var(--cream)",
                  }}
                />
              </div>
              <div className="font-mono text-[10px] w-10 text-right tabular-nums">
                {feature.rawWeight.toFixed(3)}
              </div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Transparency Strip</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">TIMING BOARD</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { l: "Model", v: modelUsed },
            { l: "F1 Score", v: metrics.f1.toFixed(3) },
            { l: "Precision", v: metrics.precision.toFixed(3) },
            { l: "Recall", v: metrics.recall.toFixed(3) },
            { l: "ROC-AUC", v: metrics.auc.toFixed(3) },
          ].map((item) => (
            <div key={item.l} className="border border-black/15 p-4">
              <div className="text-tag">{item.l}</div>
              <div className="font-mono text-xl md:text-2xl mt-2 tabular-nums break-words">
                {item.v}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 grid md:grid-cols-3 gap-3 text-xs">
          <div className="border-t border-black/15 pt-2">
            <div className="text-tag">Training Races</div>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-widest">
              {trainingData.races.join(" . ")}
            </p>
          </div>
          <div className="border-t border-black/15 pt-2">
            <div className="text-tag">Rows</div>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-widest">
              {trainingData.rows} driver-race rows
            </p>
          </div>
          <div className="border-t border-black/15 pt-2">
            <div className="text-tag">Validation</div>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-widest">
              {trainingData.cvMethod}
            </p>
          </div>
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-10 relative">
        <div className="text-tag mb-2">Honest Disclosures</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">LIMITATIONS</h2>
        <div className="grid md:grid-cols-2 gap-x-8 gap-y-3 max-w-5xl text-xs leading-relaxed">
          {limitations.map((text, index) => (
            <p key={index}>
              <span className="text-[var(--redorange)] mr-2">/</span>
              {text}
            </p>
          ))}
        </div>
        <div className="absolute bottom-4 right-6 text-5xl opacity-[0.04] pointer-events-none font-poster">
          {race?.flag ?? "PRED"}
        </div>
      </section>
    </PageShell>
  );
}
