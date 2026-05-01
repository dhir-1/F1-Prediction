import { createFileRoute } from "@tanstack/react-router";
import { PageShell } from "@/components/PageShell";
import { Checker } from "@/components/Checker";
import { MIAMI_PREDICTION, driverByCode, RACES } from "@/lib/data";

export const Route = createFileRoute("/prediction")({
  head: () => ({
    meta: [
      { title: "Miami GP Prediction — Dhir's Pit Wall" },
      { name: "description", content: "Predicted podium and full grid for the 2026 Miami Grand Prix." },
      { property: "og:title", content: "Miami GP Prediction — Dhir's Pit Wall" },
      { property: "og:description", content: "Predicted podium and full grid for the 2026 Miami GP." },
    ],
  }),
  component: PredictionPage,
});

function PredictionPage() {
  const miami = RACES.find((r) => r.round === 6)!;
  const { podium, grid, podiumProb, features, metrics } = MIAMI_PREDICTION;

  return (
    <PageShell>
      {/* HERO */}
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-20 relative overflow-hidden">
        <div className="text-tag mb-4">Round 06 · USA 🇺🇸</div>
        <h1 className="font-poster leading-[0.85] text-[14vw] md:text-[10rem] tracking-wider">
          <span className="block">MIAMI GP</span>
          <span className="block italic text-[var(--redorange)]">PREDICTED.</span>
        </h1>
        <div className="mt-6 inline-block bg-[var(--redorange)] text-white px-5 py-2 font-display font-bold tracking-[0.2em] uppercase text-sm">
          Pre-Qualifying Forecast
        </div>
        <div className="mt-6 font-mono text-xs opacity-70 tracking-widest uppercase">
          {miami.circuit} · {miami.laps} Laps · {miami.lengthKm.toFixed(3)} km
        </div>
      </section>

      <Checker />

      {/* PODIUM */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Predicted Podium</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-10 tracking-wider">THE TOP THREE</h2>
        <div className="grid grid-cols-3 gap-4 md:gap-8 items-end">
          {[1, 0, 2].map((idx) => {
            const p = podium[idx];
            const d = driverByCode(p.code);
            const tall = idx === 0; // P1 in middle visually
            return (
              <div
                key={p.code}
                className={`border-l border-r border-black/15 px-3 md:px-6 ${tall ? "pb-12" : "pb-4"}`}
                style={{ borderLeft: `4px solid ${d.color}` }}
              >
                <div className="font-poster text-3xl md:text-5xl tracking-wider">
                  P{idx + 1}
                </div>
                <div className={`font-mono font-bold ${tall ? "text-7xl md:text-9xl" : "text-5xl md:text-7xl"} leading-none mt-2`}>
                  {d.code}
                </div>
                <div className="font-display font-bold uppercase mt-2 text-sm">{d.name}</div>
                <div className="text-[11px] uppercase tracking-widest opacity-60">{d.team}</div>
                <div className="mt-3 text-[var(--redorange)] font-mono font-bold">
                  {p.confidence}% conf.
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Checker />

      {/* FULL GRID */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Predicted Order</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">FULL GRID FORECAST</h2>
        <div>
          {grid.map((code, i) => {
            const d = driverByCode(code);
            const prob = podiumProb[code] ?? 0;
            return (
              <div
                key={code}
                className="grid grid-cols-[40px_80px_1fr_140px] md:grid-cols-[60px_120px_1fr_220px] items-center gap-3 py-3 border-t border-black/15"
                style={{ borderLeft: `4px solid ${d.color}` }}
              >
                <div className="font-mono text-lg md:text-xl pl-2 opacity-70">P{i + 1}</div>
                <div className="font-mono font-bold text-lg md:text-2xl">{d.code}</div>
                <div className="min-w-0">
                  <div className="font-display font-bold uppercase truncate">{d.name}</div>
                  <div className="text-[10px] uppercase tracking-widest opacity-60">{d.team}</div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-black/10">
                    <div
                      className="h-full bar-anim"
                      style={{ background: "var(--redorange)", width: `${prob}%` }}
                    />
                  </div>
                  <div className="font-mono text-xs w-10 text-right tabular-nums">{prob}%</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Checker />

      {/* FEATURE IMPORTANCE */}
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Model Internals</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">FEATURE WEIGHT</h2>
        <div className="space-y-3">
          {features.map((f, i) => (
            <div key={f.name} className="flex items-center gap-4">
              <div className="font-mono text-[10px] tracking-widest uppercase w-44 md:w-56 opacity-80">
                {String(i + 1).padStart(2, "0")} · {f.name}
              </div>
              <div className="flex-1 h-5 bg-white/5 relative">
                <div
                  className="h-full bar-anim"
                  style={{
                    width: `${f.weight}%`,
                    background: i === 0 ? "var(--redorange)" : "var(--cream)",
                  }}
                />
              </div>
              <div className="font-mono text-xs w-10 text-right tabular-nums">{f.weight}</div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      {/* MODEL TRANSPARENCY */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Transparency Strip</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">TIMING BOARD</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { l: "Model", v: "XGBoost" },
            { l: "F1 Score", v: metrics.f1.toFixed(3) },
            { l: "Precision", v: metrics.precision.toFixed(3) },
            { l: "AUC", v: metrics.auc.toFixed(3) },
          ].map((x) => (
            <div key={x.l} className="border border-black/15 p-5">
              <div className="text-tag">{x.l}</div>
              <div className="font-mono text-3xl md:text-5xl mt-2 tabular-nums">{x.v}</div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      {/* LIMITATIONS */}
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16 relative">
        <div className="text-tag mb-3">Honest Disclosures</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">LIMITATIONS</h2>
        <div className="grid md:grid-cols-2 gap-x-12 gap-y-4 max-w-5xl text-sm leading-relaxed">
          {[
            "Trained on only 66 rows from the first three races of 2026 — variance is enormous and overfitting is real.",
            "No live qualifying data is integrated; predictions update only after each completed Grand Prix.",
            "Weather is approximated via a single index value; sudden changes in track temperature aren't modelled.",
            "Driver-team chemistry shifts (mid-season swaps, contract drama) are invisible to the feature set.",
            "Tyre compound choice is encoded as ordinal; nuanced strategy interactions are not captured.",
            "Safety cars and red flags are statistically smoothed; chaotic races deviate sharply from forecast.",
          ].map((t, i) => (
            <p key={i}>
              <span className="text-[var(--redorange)] mr-2">—</span>
              {t}
            </p>
          ))}
        </div>
        <div className="absolute bottom-4 right-6 text-6xl opacity-[0.04] pointer-events-none">🌸</div>
      </section>
    </PageShell>
  );
}
