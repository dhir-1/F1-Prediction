import { createFileRoute } from "@tanstack/react-router";
import { PageShell } from "@/components/PageShell";
import { Checker } from "@/components/Checker";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About the Model — Dhir's Pit Wall" },
      { name: "description", content: "How the prediction model works: features, training, scores." },
      { property: "og:title", content: "About the Model — Dhir's Pit Wall" },
      { property: "og:description", content: "How the prediction model works." },
    ],
  }),
  component: AboutPage,
});

const FEATURES = [
  ["Grid Position", "Where the driver starts. The single strongest signal in race outcomes."],
  ["Recent Form", "Rolling average of finishes over the last 3 races."],
  ["Team Pace Index", "Composite of team's average qualifying delta to pole."],
  ["Quali Delta", "Gap to pole position in seconds, normalised per circuit."],
  ["Tyre Strategy", "Predicted compound sequence based on track and weather."],
  ["Track History", "Driver's average finish at this circuit across all eras."],
  ["Driver Rating", "Elo-style rating updated after every race weekend."],
  ["DNF Risk", "Probability of mechanical failure based on team reliability."],
  ["Weather Score", "Single index for rain probability and air temperature."],
  ["Pit Stop Avg", "Team's average pit stop time, in seconds."],
  ["Sector 2 Pace", "Best Sector 2 time relative to fastest, used for race pace proxy."],
  ["Car Upgrades", "Boolean flag for whether team brought upgrades this weekend."],
];

const TECH = ["FastF1", "XGBoost", "scikit-learn", "React", "Python"];

function AboutPage() {
  return (
    <PageShell>
      {/* HERO */}
      <section className="px-6 md:px-16 py-20">
        <div className="text-tag mb-4">Documentation</div>
        <h1 className="font-poster leading-[0.85] text-[12vw] md:text-[9rem] tracking-wider">
          ABOUT THE <span className="text-[var(--redorange)] italic">MODEL</span>
        </h1>
      </section>

      <Checker />

      {/* TWO COLUMN ARTICLE */}
      <section className="px-6 md:px-16 py-16 grid md:grid-cols-2 gap-12">
        <div className="space-y-4 text-base leading-relaxed">
          <div className="text-tag">The Approach</div>
          <p>
            Dhir's Pit Wall is a hand-built prediction engine for the 2026 Formula One season.
            It scrapes timing data from the FastF1 API after every Grand Prix, derives a
            twelve-feature dataset per driver per race, and trains a gradient-boosted classifier
            to predict the probability of each driver finishing on the podium.
          </p>
          <p>
            The model deliberately stays small. There are only twenty-two drivers and a finite
            number of races each year — adding hundreds of features to sixty-six rows of data
            would just memorise the noise. Instead the focus is on a tight set of explainable
            features: where you start, how fast your car is, and how you've been driving lately.
          </p>
          <p>
            Predictions are regenerated weekly using a leave-one-race-out cross-validation
            scheme. The current numbers reflect training on Australia and China, with Japan
            held out as the test set. The full season will retrain after every round.
          </p>
        </div>
        <div className="md:border-l-2 md:border-[var(--redorange)] md:pl-12 flex items-center">
          <p className="font-serif italic text-3xl md:text-5xl leading-tight text-[var(--redorange)]">
            "66 rows. 3 races. 12 features. One prediction."
          </p>
        </div>
      </section>

      <Checker />

      {/* FEATURES GRID */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">The Twelve Features</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-10 tracking-wider">WHAT IT KNOWS</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {FEATURES.map(([name, desc]) => (
            <div key={name} className="border border-black/20 p-5">
              <div className="font-mono text-[11px] tracking-widest uppercase text-[var(--redorange)] font-bold">
                {name}
              </div>
              <p className="text-sm mt-2 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      {/* LORO DIAGRAM */}
      <section className="bg-[var(--charcoal)] text-[var(--cream)] px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Validation Strategy</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-10 tracking-wider">LEAVE-ONE-RACE-OUT</h2>
        <div className="flex items-center justify-center gap-2 md:gap-6 flex-wrap">
          {[
            { code: "AUS", role: "TRAIN" },
            { code: "CHN", role: "TRAIN" },
            { code: "JPN", role: "TEST" },
          ].map((b, i) => (
            <div key={b.code} className="flex items-center gap-2 md:gap-6">
              <div
                className={`border-2 px-6 md:px-10 py-6 md:py-10 ${b.role === "TEST" ? "border-[var(--redorange)] bg-[var(--redorange)]/15" : "border-white/30"}`}
              >
                <div className="font-poster text-4xl md:text-6xl tracking-widest">{b.code}</div>
                <div className="font-mono text-[10px] tracking-widest mt-1 opacity-70">{b.role}</div>
              </div>
              {i < 2 && <div className="font-mono text-2xl opacity-60">→</div>}
            </div>
          ))}
        </div>
        <div className="text-center mt-6 font-mono text-[10px] tracking-widest opacity-50 uppercase">
          Each round rotates through being the test set, results averaged.
        </div>
      </section>

      <Checker />

      {/* SCORES */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Actual Scores</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">THE NUMBERS</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { l: "F1 Score", v: "0.857" },
            { l: "Precision", v: "0.750" },
            { l: "Recall", v: "1.000" },
            { l: "AUC", v: "0.968" },
          ].map((x) => (
            <div key={x.l} className="border border-black/15 p-5">
              <div className="text-tag">{x.l}</div>
              <div className="font-mono text-4xl md:text-6xl mt-2 tabular-nums">{x.v}</div>
            </div>
          ))}
        </div>
      </section>

      <Checker />

      {/* TECH STACK */}
      <section className="px-6 md:px-16 py-16">
        <div className="text-tag mb-3">Built With</div>
        <h2 className="font-poster text-5xl md:text-7xl mb-8 tracking-wider">TECH STACK</h2>
        <div className="flex flex-wrap gap-3">
          {TECH.map((t) => (
            <span
              key={t}
              className="bg-black text-white px-5 py-3 font-display font-bold uppercase tracking-[0.18em] text-sm"
            >
              {t}
            </span>
          ))}
        </div>
      </section>
    </PageShell>
  );
}
