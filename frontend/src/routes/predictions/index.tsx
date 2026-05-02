import { createFileRoute, Link } from "@tanstack/react-router";
import { Checker } from "@/components/Checker";
import { PageShell } from "@/components/PageShell";
import { driverByCode, useSiteData } from "@/lib/data";

export const Route = createFileRoute("/predictions/")({
  head: () => ({
    meta: [
      { title: "Race Predictions - Dhir's Pit Wall" },
      { name: "description", content: "All published machine learning race predictions for the 2026 F1 season." },
    ],
  }),
  component: PredictionsBoard,
});

function PredictionsBoard() {
  const { predictions, races, drivers } = useSiteData();

  return (
    <PageShell>
      <section className="px-6 md:px-16 py-20">
        <div className="text-tag mb-4">Model Output</div>
        <h1 className="font-poster leading-[0.85] text-[12vw] md:text-[9rem] tracking-wider">
          RACE <span className="text-[var(--redorange)] italic">FORECASTS</span>
        </h1>
        <p className="mt-6 font-serif italic text-xl md:text-2xl max-w-3xl">
          The central board for all published machine learning predictions across the 2026 season.
        </p>
      </section>

      <Checker />

      <section className="px-6 md:px-16 py-16 min-h-[50vh]">
        {predictions.length === 0 ? (
          <div className="text-center py-20 border border-black/10">
            <h2 className="font-poster text-4xl text-black/40">NO PREDICTIONS PUBLISHED</h2>
            <p className="font-mono text-sm opacity-50 mt-4">Check back closer to the next race weekend.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {predictions.map((pred) => {
              const race = races.find((r) => r.round === pred.round);
              const p1 = pred.podium[0];
              const p1Driver = p1 ? driverByCode(p1.code, drivers) : null;

              return (
                <Link
                  key={pred.slug}
                  to={`/predictions/${pred.slug}`}
                  className="group border border-black/20 hover:border-[var(--redorange)] transition-colors flex flex-col"
                >
                  <div className="p-6 flex-1">
                    <div className="flex items-start justify-between gap-4 mb-8">
                      <div>
                        <div className="font-mono text-[10px] tracking-widest opacity-60 uppercase mb-2">
                          Round {String(pred.round).padStart(2, "0")}
                        </div>
                        <h3 className="font-display font-bold uppercase text-2xl leading-tight group-hover:text-[var(--redorange)] transition-colors">
                          {pred.raceName}
                        </h3>
                      </div>
                      <div className="bg-black text-white px-3 py-1 font-mono text-[9px] tracking-wider uppercase shrink-0">
                        {pred.status}
                      </div>
                    </div>
                    
                    {p1Driver && (
                      <div className="pt-6 border-t border-black/10" style={{ borderLeft: `4px solid ${p1Driver.color}` }}>
                        <div className="pl-4">
                          <div className="font-mono text-[10px] opacity-60 mb-1">Predicted Winner</div>
                          <div className="font-poster text-4xl tracking-wider">{p1Driver.code}</div>
                          <div className="font-display font-bold uppercase text-sm mt-1">{p1Driver.name}</div>
                          <div className="font-mono text-[10px] opacity-60 mt-2">{p1.confidence.toFixed(1)}% Confidence</div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="bg-[var(--charcoal)] text-[var(--cream)] px-6 py-3 font-mono text-[10px] tracking-widest uppercase flex justify-between items-center group-hover:bg-[var(--redorange)] transition-colors">
                    <span>{race ? new Date(race.date).toLocaleDateString() : pred.date}</span>
                    <span>View Board →</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </PageShell>
  );
}
