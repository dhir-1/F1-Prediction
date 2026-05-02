import { createFileRoute } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { useSiteData } from "@/lib/data";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About the Model - Dhir's Pit Wall" },
      { name: "description", content: "How the F1 2026 prediction model works: features, training, and evaluation." },
    ],
  }),
  component: AboutPage,
});

function AboutPage() {
  const { featureDetails, techStack, predictions, races } = useSiteData();
  
  const completedRaces = races.filter((r) => r.status === "completed");
  const trainingRows = completedRaces.length * 22; // 22 drivers per race
  const latestPrediction = predictions[predictions.length - 1];

  return (
    <PageShell>
      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Documentation</div>
        <h1 className="font-poster leading-[0.85] text-[12vw] md:text-[8rem] tracking-wider">
          ABOUT THE <span className="text-[var(--redorange)] italic">MODEL</span>
        </h1>
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10 grid md:grid-cols-2 gap-8">
        <div className="space-y-4 text-sm leading-relaxed">
          <div className="text-tag">The Approach</div>
          <p>
            Dhir's Pit Wall uses FastF1 race data from earlier rounds to build a driver-by-driver training table for the 2026 season. Each row is engineered from information that should be knowable before lights out, then scored by a shortlist of models including XGBoost and Random Forest.
          </p>
          <p>
            The project is intentionally honest about the sample size. The model is there to support the call, surface the strongest signals, and make the reasoning visible — not to pretend we have absolute certainty.
          </p>
          <p>
            Each prediction page is published in a "Pre-Qualifying" state using estimated grid slots, then updated to a "Final Forecast" state once real grid positions are set. 
          </p>
        </div>
        <div className="md:border-l-2 md:border-[var(--redorange)] md:pl-8 flex items-center">
          <p className="font-serif italic text-2xl md:text-4xl leading-tight text-[var(--redorange)]">
            "{trainingRows} rows. {completedRaces.length} races. {featureDetails.length} engineered features."
          </p>
        </div>
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">The Feature Set</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">WHAT IT KNOWS</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {featureDetails.map((feature) => (
            <div key={feature.key} className="border border-black/20 p-4">
              <div className="font-mono text-[10px] tracking-widest uppercase text-[var(--redorange)] font-bold">
                {feature.name}
              </div>
              <p className="text-xs mt-2 leading-relaxed opacity-80">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Validation Strategy</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">LEAVE-ONE-RACE-OUT</h2>
        <div className="flex items-center gap-2 md:gap-4 flex-wrap">
          {completedRaces.slice(-3).map((race, index, arr) => (
            <div key={race.round} className="flex items-center gap-2 md:gap-4">
              <div
                className={`border-2 px-4 md:px-6 py-4 md:py-6 ${index === arr.length - 1 ? "border-[var(--redorange)] bg-[var(--redorange)]/15" : "border-white/30"}`}
              >
                <div className="font-poster text-3xl md:text-5xl tracking-widest">{race.flag}</div>
                <div className="font-mono text-[9px] tracking-widest mt-1 opacity-70">
                  {index === arr.length - 1 ? "TEST" : "TRAIN"}
                </div>
              </div>
              {index < arr.length - 1 && <div className="font-mono text-xl opacity-60">-&gt;</div>}
            </div>
          ))}
          {completedRaces.length < 3 && (
            <div className="text-sm font-mono opacity-50 ml-4 border border-white/20 px-4 py-2">
              Waiting for more races to build the LORO pipeline.
            </div>
          )}
        </div>
        <div className="mt-4 font-mono text-[9px] tracking-widest opacity-50 uppercase">
          Each round rotates through the test slot so the next race is always predicted from prior ones.
        </div>
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Latest Model Performance</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">THE NUMBERS</h2>
        {latestPrediction ? (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { l: "F1 Score", v: latestPrediction.metrics.f1.toFixed(3) },
                { l: "Precision", v: latestPrediction.metrics.precision.toFixed(3) },
                { l: "Recall", v: latestPrediction.metrics.recall.toFixed(3) },
                { l: "ROC-AUC", v: latestPrediction.metrics.auc.toFixed(3) },
              ].map((item) => (
                <div key={item.l} className="border border-black/15 p-4">
                  <div className="text-tag">{item.l}</div>
                  <div className="font-mono text-3xl md:text-5xl mt-2 tabular-nums">{item.v}</div>
                </div>
              ))}
            </div>
            <div className="font-mono text-[10px] mt-4 opacity-50 uppercase tracking-widest">
              From {latestPrediction.raceName} Forecast
            </div>
          </div>
        ) : (
          <div className="p-6 border border-black/10 font-mono text-sm opacity-50">
            No published predictions yet. Scores will appear here once the first forecast runs.
          </div>
        )}
      </section>

      <Checker />

      <section className="px-4 md:px-8 py-10">
        <div className="text-tag mb-2">Built With</div>
        <h2 className="font-poster text-4xl md:text-5xl mb-6 tracking-wider">TECH STACK</h2>
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech) => (
            <span
              key={tech}
              className="bg-black text-white px-3 py-2 font-display font-bold uppercase tracking-[0.1em] text-xs"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
