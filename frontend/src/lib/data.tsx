import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

// ─── Types (matching backend Pydantic models) ────────────────────────────────

export interface Driver {
  code: string;
  name: string;
  team: string;
  color: string;
  points: number;
}

export interface Race {
  round: number;
  slug: string;
  name: string;
  country: string;
  flag: string;
  circuit: string;
  date: string;
  laps: number;
  lengthKm: number;
  status: "completed" | "cancelled" | "next" | "upcoming";
  winner?: string;
  podium?: [string, string, string];
  fastestLap?: string;
  note?: string;
  winnerImage?: string;
}

export interface FeatureDetail {
  key: string;
  name: string;
  description: string;
}

export interface PredictionPodiumEntry {
  code: string;
  team: string;
  confidence: number;
  pos: number;
}

export interface PredictionGridEntry {
  code: string;
  team: string;
  probability: number;
  predictedPosition: number;
  gridPosition: number;
  gridSource: string;
}

export interface FeatureWeight {
  key: string;
  name: string;
  weight: number;
  rawWeight: number;
}

export interface PredictionMetrics {
  f1: number;
  precision: number;
  recall: number;
  auc: number;
}

export interface TrainingData {
  races: string[];
  rows: number;
  cvMethod: string;
}

export interface RacePrediction {
  slug: string;
  raceName: string;
  round: number;
  circuit: string;
  date: string;
  status: string;
  qualifyingDone: boolean;
  modelUsed: string;
  podium: PredictionPodiumEntry[];
  grid: PredictionGridEntry[];
  podiumProb: Record<string, number>;
  features: FeatureWeight[];
  metrics: PredictionMetrics;
  trainingData: TrainingData;
  limitations: string[];
}

export interface SiteData {
  drivers: Driver[];
  races: Race[];
  featureDetails: FeatureDetail[];
  techStack: string[];
  predictions: RacePrediction[];
  /** Backward compat — first available prediction (used by legacy pages until Phase 3) */
  miamiPrediction: RacePrediction;
}

// ─── Context ─────────────────────────────────────────────────────────────────

const SiteDataContext = createContext<SiteData | null>(null);

export function SiteDataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<SiteData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/site-data")
      .then((res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return res.json();
      })
      .then((raw) => {
        const predictions: RacePrediction[] = raw.predictions ?? [];
        const miamiPrediction =
          predictions.find((p) => p.slug === "miami-grand-prix") ?? predictions[0] ?? null;
        setData({
          drivers: raw.drivers,
          races: raw.races,
          featureDetails: raw.featureDetails,
          techStack: raw.techStack,
          predictions,
          miamiPrediction,
        });
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--charcoal)] text-[var(--cream)] px-4">
        <div className="max-w-md text-center">
          <h1 className="font-poster text-6xl text-[var(--redorange)]">PIT STOP</h1>
          <p className="mt-4 font-mono text-sm opacity-70">Failed to load data from the backend.</p>
          <p className="mt-2 font-mono text-xs opacity-50">{error}</p>
          <button onClick={() => window.location.reload()} className="btn-stamp mt-6">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--charcoal)] text-[var(--cream)]">
        <div className="text-center">
          <div className="font-poster text-4xl tracking-wider animate-pulse">
            DHIR'S <span className="text-[var(--redorange)] italic">PIT WALL</span>
          </div>
          <div className="mt-4 font-mono text-[10px] tracking-[0.3em] uppercase opacity-60">
            Loading season data…
          </div>
        </div>
      </div>
    );
  }

  return <SiteDataContext.Provider value={data}>{children}</SiteDataContext.Provider>;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useSiteData(): SiteData {
  const ctx = useContext(SiteDataContext);
  if (!ctx) throw new Error("useSiteData must be used within SiteDataProvider");
  return ctx;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function driverByCode(code: string, drivers: Driver[]): Driver {
  return (
    drivers.find((d) => d.code === code) ?? {
      code,
      name: code,
      team: "Unknown",
      color: "#888888",
      points: 0,
    }
  );
}

export function standings(drivers: Driver[]): Driver[] {
  return [...drivers].sort((a, b) => b.points - a.points);
}

export function constructorStandings(
  drivers: Driver[],
): { team: string; points: number; color: string }[] {
  const map = new Map<string, { team: string; points: number; color: string }>();
  for (const d of drivers) {
    const existing = map.get(d.team);
    if (existing) {
      existing.points += d.points;
    } else {
      map.set(d.team, { team: d.team, points: d.points, color: d.color });
    }
  }
  return [...map.values()].sort((a, b) => b.points - a.points);
}

export function getPredictionBySlug(
  slug: string,
  predictions: RacePrediction[],
): RacePrediction | undefined {
  return predictions.find((p) => p.slug === slug);
}
