import { createFileRoute } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { driverByCode, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/prediction")({
  head: () => ({
    meta: [
      { title: "Miami GP Prediction - Dhir's Pit Wall" },
      { name: "description", content: "Predicted podium and full grid for the 2026 Miami Grand Prix." },
      { property: "og:title", content: "Miami GP Prediction - Dhir's Pit Wall" },
      { property: "og:description", content: "Predicted podium and full grid for the 2026 Miami GP." },
    ],
  }),
  component: PredictionPage,
});

function PredictionPage() {
  const siteData = useSiteData();
  const miamiPrediction = siteData.miamiPrediction;
  const miami = siteData.races.find((race) => race.round === miamiPrediction.round)!;
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
  } = miamiPrediction;

  const podiumDisplay = podium;

  return (
    <PageShell>
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-20 relative overflow-hidden">
        <div className="text-tag mb-4">
          Round {String(miami.round).padStart(2, "0")} . {miami.country}
        </div>
        <h1 className="font-poster leading-[0.85] text-[14vw] md:text-[10rem] tracking-wider">
          <span className="block">MIAMI GP</span>
          <span className="block italic text-[var(--redorange)]">PREDICTED.</span>
        </h1>
        <div className="mt-6 inline-block bg-[var(--redorange)] text-white px-5 py-2 font-display font-bold tracking-[0.2em] uppercase text-sm">
          {status}
        </div>
        <div className="mt-6 font-mono text-xs opacity-70 tracking-widest uppercase">
          {miami.circuit} . {miami.laps} Laps . {miami.lengthKm.toFixed(3)} km
        </div>
        {!qualifyingDone && (
          <p className="mt-4 max-w-2xl text-sm text-white/70 leading-relaxed">
            Grid positions are still estimated from 2026 qualifying form. This page is set up to
            refresh cleanly once you rerun `backend/scripts/generate_prediction.py` after Miami
            qualifying.
          </p>
        )}
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Predicted Podium</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-10 tracking-wider">THE TOP THREE</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-8 items-end">
          {podiumDisplay.map((pick) => {
            const driver = driverByCode(pick.code, siteData.drivers);
            const tall = pick.pos === 1;
            const orderClass =
              pick.pos === 1 ? "order-1 sm:order-2" : pick.pos === 2 ? "order-2 sm:order-1" : "order-3";

            return (
              <div
                key={pick.code}
                className={`border-l border-r border-black/15 px-3 md:px-6 ${orderClass} ${tall ? "pb-12" : "pb-4"}`}
                style={{ borderLeft: `4px solid ${driver.color}` }}
              >
                <div className="font-poster text-3xl md:text-5xl tracking-wider">P{pick.pos}</div>
                <div
                  className={`font-mono font-bold ${tall ? "text-7xl md:text-9xl" : "text-5xl md:text-7xl"} leading-none mt-2`}
                >
                  {driver.code}
                </div>
                <div className="font-display font-bold uppercase mt-2 text-sm">{driver.name}</div>
                <div className="text-[11px] uppercase tracking-widest opacity-60">{driver.team}</div>
                <div className="mt-3 text-[var(--redorange)] font-mono font-bold">
                  {pick.confidence.toFixed(1)}% conf.
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Predicted Order</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">FULL GRID FORECAST</h2>
        <div>
          {grid.map((entry) => {
            const driver = driverByCode(entry.code, siteData.drivers);

            return (
              <div
                key={entry.code}
                className="grid grid-cols-[34px_56px_1fr_96px] md:grid-cols-[60px_120px_1fr_220px] items-center gap-3 py-3 border-t border-black/15"
                style={{ borderLeft: `4px solid ${driver.color}` }}
              >
                <div className="font-mono text-lg md:text-xl pl-2 opacity-70">P{entry.predictedPosition}</div>
                <div className="font-mono font-bold text-lg md:text-2xl">{driver.code}</div>
                <div className="min-w-0">
                  <div className="font-display font-bold uppercase truncate">{driver.name}</div>
                  <div className="text-[10px] uppercase tracking-widest opacity-60">{driver.team}</div>
                  <div className="text-[10px] uppercase tracking-widest opacity-40 mt-1">
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
                  <div className="font-mono text-xs w-12 text-right tabular-nums">
                    {entry.probability.toFixed(1)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Model Internals</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">FEATURE WEIGHT</h2>
        <div className="space-y-3">
          {features.map((feature, index) => (
            <div key={feature.key} className="flex items-center gap-4">
              <div className="font-mono text-[10px] tracking-widest uppercase w-44 md:w-56 opacity-80">
                {String(index + 1).padStart(2, "0")} . {feature.name}
              </div>
              <div className="flex-1 h-5 bg-white/5 relative">
                <div
                  className="h-full bar-anim"
                  style={{
                    width: `${feature.weight}%`,
                    background: index === 0 ? "var(--redorange)" : "var(--cream)",
                  }}
                />
              </div>
              <div className="font-mono text-xs w-12 text-right tabular-nums">
                {feature.rawWeight.toFixed(3)}
              </div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Transparency Strip</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">TIMING BOARD</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { l: "Model", v: modelUsed },
            { l: "F1 Score", v: metrics.f1.toFixed(3) },
            { l: "Precision", v: metrics.precision.toFixed(3) },
            { l: "Recall", v: metrics.recall.toFixed(3) },
            { l: "ROC-AUC", v: metrics.auc.toFixed(3) },
          ].map((item) => (
            <div key={item.l} className="border border-black/15 p-5">
              <div className="text-tag">{item.l}</div>
              <div className="font-mono text-2xl md:text-4xl mt-2 tabular-nums break-words">
                {item.v}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-6 grid md:grid-cols-3 gap-4 text-sm">
          <div className="border-t border-black/15 pt-3">
            <div className="text-tag">Training Races</div>
            <p className="mt-2 font-mono text-xs uppercase tracking-widest">
              {trainingData.races.join(" . ")}
            </p>
          </div>
          <div className="border-t border-black/15 pt-3">
            <div className="text-tag">Rows</div>
            <p className="mt-2 font-mono text-xs uppercase tracking-widest">
              {trainingData.rows} driver-race rows
            </p>
          </div>
          <div className="border-t border-black/15 pt-3">
            <div className="text-tag">Validation</div>
            <p className="mt-2 font-mono text-xs uppercase tracking-widest">
              {trainingData.cvMethod}
            </p>
          </div>
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16 relative">
        <div className="text-tag mb-3">Honest Disclosures</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">LIMITATIONS</h2>
        <div className="grid md:grid-cols-2 gap-x-12 gap-y-4 max-w-5xl text-sm leading-relaxed">
          {limitations.map((text, index) => (
            <p key={index}>
              <span className="text-[var(--redorange)] mr-2">/</span>
              {text}
            </p>
          ))}
        </div>
        <div className="absolute bottom-4 right-6 text-6xl opacity-[0.04] pointer-events-none">MIA</div>
      </section>
    </PageShell>
  );
}
