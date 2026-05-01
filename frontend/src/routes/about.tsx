import { createFileRoute } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { useSiteData } from "@/lib/data";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About the Model - Dhir's Pit Wall" },
      { name: "description", content: "How the prediction model works: features, training, and evaluation." },
      { property: "og:title", content: "About the Model - Dhir's Pit Wall" },
      { property: "og:description", content: "How the prediction model works." },
    ],
  }),
  component: AboutPage,
});

function AboutPage() {
  const siteData = useSiteData();

  return (
    <PageShell>
      <section className="px-6 md:px-16 py-20">
        <div className="text-tag mb-4">Documentation</div>
        <h1 className="font-poster leading-[0.85] text-[12vw] md:text-[9rem] tracking-wider">
          ABOUT THE <span className="text-[var(--redorange)] italic">MODEL</span>
        </h1>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16 grid md:grid-cols-2 gap-12">
        <div className="space-y-4 text-base leading-relaxed">
          <div className="text-tag">The Approach</div>
          <p>
            Dhir's Pit Wall uses FastF1 race data from Australia, China, and Japan to build a
            small driver-by-driver training table for the 2026 season. Each row is engineered from
            information that should be knowable before lights out, then scored by a shortlist of
            models including XGBoost and Random Forest.
          </p>
          <p>
            The current Miami page is intentionally honest about the sample size. With only 66
            training rows, the goal is not to pretend we have certainty. The model is there to
            support the call, surface the strongest signals, and make the reasoning visible.
          </p>
          <p>
            Miami is the first weekend under the new energy management regulations, so the feature
            set includes a dedicated regulation flag. When qualifying is complete, rerunning
            `backend/scripts/generate_prediction.py` swaps the estimated grid for the real one and
            upgrades the site from pre-qualifying to final prediction mode.
          </p>
        </div>
        <div className="md:border-l-2 md:border-[var(--redorange)] md:pl-12 flex items-center">
          <p className="font-serif italic text-3xl md:text-5xl leading-tight text-[var(--redorange)]">
            "66 rows. 3 races. 12 features plus the Miami regs flag."
          </p>
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">The Feature Set</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-10 tracking-wider">WHAT IT KNOWS</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {siteData.featureDetails.map((feature) => (
            <div key={feature.key} className="border border-black/20 p-5">
              <div className="font-mono text-[11px] tracking-widest uppercase text-[var(--redorange)] font-bold">
                {feature.name}
              </div>
              <p className="text-sm mt-2 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Validation Strategy</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-10 tracking-wider">LEAVE-ONE-RACE-OUT</h2>
        <div className="flex items-center justify-center gap-2 md:gap-6 flex-wrap">
          {[
            { code: "AUS", role: "TRAIN" },
            { code: "CHN", role: "TRAIN" },
            { code: "JPN", role: "TEST" },
          ].map((block, index) => (
            <div key={block.code} className="flex items-center gap-2 md:gap-6">
              <div
                className={`border-2 px-6 md:px-10 py-6 md:py-10 ${block.role === "TEST" ? "border-[var(--redorange)] bg-[var(--redorange)]/15" : "border-white/30"}`}
              >
                <div className="font-poster text-4xl md:text-6xl tracking-widest">{block.code}</div>
                <div className="font-mono text-[10px] tracking-widest mt-1 opacity-70">{block.role}</div>
              </div>
              {index < 2 && <div className="font-mono text-2xl opacity-60">-&gt;</div>}
            </div>
          ))}
        </div>
        <div className="text-center mt-6 font-mono text-[10px] tracking-widest opacity-50 uppercase">
          Each round rotates through the test slot so Miami is always predicted from earlier races.
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Actual Scores</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">THE NUMBERS</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { l: "F1 Score", v: siteData.miamiPrediction.metrics.f1.toFixed(3) },
            { l: "Precision", v: siteData.miamiPrediction.metrics.precision.toFixed(3) },
            { l: "Recall", v: siteData.miamiPrediction.metrics.recall.toFixed(3) },
            { l: "ROC-AUC", v: siteData.miamiPrediction.metrics.auc.toFixed(3) },
          ].map((item) => (
            <div key={item.l} className="border border-black/15 p-5">
              <div className="text-tag">{item.l}</div>
              <div className="font-mono text-4xl md:text-6xl mt-2 tabular-nums">{item.v}</div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Built With</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">TECH STACK</h2>
        <div className="flex flex-wrap gap-3">
          {siteData.techStack.map((tech) => (
            <span
              key={tech}
              className="bg-black text-white px-5 py-3 font-display font-bold uppercase tracking-[0.18em] text-sm"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
