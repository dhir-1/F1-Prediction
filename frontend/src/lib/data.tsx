import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

// ─── Types (matching backend Pydantic models) ────────────────────────────────

export interface Driver {
  code: string;
  name: string;
  team: string;
  color: string;
  points: number;
  number?: string | null;
  headshot?: string | null;
  broadcastName?: string | null;
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
  actualResult?: { pos: number; driver: string }[];
  pitWallNotes?: string[];
}

export interface SiteData {
  drivers: Driver[];
  races: Race[];
  featureDetails: FeatureDetail[];
  techStack: string[];
  predictions: RacePrediction[];
  /** Backward compat — first available prediction (used by legacy pages until Phase 3) */
  miamiPrediction: RacePrediction | null;
}

export const PREDICTION_BADGE = "PUBLISHED";

// ─── Context ─────────────────────────────────────────────────────────────────

const SiteDataContext = createContext<SiteData | null>(null);

export function SiteDataProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<SiteData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const API_BASE = import.meta.env.VITE_API_URL ?? "";

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/site-data`)
      .then((res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return res.json();
      })
      .then((raw) => {
        const predictions: RacePrediction[] = (raw.predictions ?? []).map((prediction: any) =>
          normalizePrediction(prediction),
        );
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
          <div className="font-poster text-4xl tracking-wider animate-pulse">PIT WALL</div>
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

function normalizePrediction(raw: any): RacePrediction {
  if (raw?.podium && raw?.grid) return raw as RacePrediction;

  const podiumSource = raw?.prediction ?? {};
  const podium = ["P1", "P2", "P3"]
    .map((key, idx) => {
      const entry = podiumSource[key];
      if (!entry) return null;
      return {
        code: entry.driver,
        team: entry.constructor ?? "",
        confidence: Number(entry.confidence ?? 0),
        pos: idx + 1,
      };
    })
    .filter(Boolean) as RacePrediction["podium"];

  const grid = (raw?.fullProbabilities ?? []).map((entry: any, idx: number) => ({
    code: entry.driver,
    team: entry.constructor ?? "",
    probability: Number(entry.podiumProb ?? 0),
    predictedPosition: idx + 1,
    gridPosition: entry.gridPosition ?? 10,
    gridSource: "Not used",
  })) as RacePrediction["grid"];

  const featureEntries = Object.entries(raw?.featureImportance ?? {}).map(([key, weight]) => ({
    key,
    name: key.replace(/_/g, " ").replace(/\b\w/g, (s) => s.toUpperCase()),
    weight: Number(weight ?? 0),
    rawWeight: Number(weight ?? 0),
  })) as RacePrediction["features"];

  const actualResult = Array.isArray(raw?.actualResult)
    ? raw.actualResult
    : raw?.actualResult && typeof raw.actualResult === "object"
      ? ["P1", "P2", "P3"]
          .map((key, idx) => raw.actualResult[key] ? { pos: idx + 1, driver: raw.actualResult[key] } : null)
          .filter(Boolean)
      : undefined;

  const fallbackName = raw?.race ?? raw?.raceName ?? `round-${raw?.round ?? "0"}`;
  const slugFromName = String(fallbackName)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

  return {
    slug: raw?.slug ?? slugFromName,
    raceName: raw?.race ?? raw?.raceName ?? fallbackName,
    round: Number(raw?.round ?? 0),
    circuit: raw?.circuit ?? "",
    date: raw?.date ?? "",
    status: raw?.qualifyingDone ? "Final Prediction" : "Pre-Qualifying Prediction",
    qualifyingDone: Boolean(raw?.qualifyingDone ?? false),
    modelUsed: raw?.modelVersion ?? raw?.modelUsed ?? "Unknown",
    podium,
    grid,
    podiumProb: Object.fromEntries(podium.map((item) => [item.code, item.confidence])),
    features: featureEntries,
    metrics: {
      f1: Number(raw?.modelMetrics?.hyperparameterTuning?.XGBoost?.optuna_f1 ?? 0),
      precision: 0,
      recall: 0,
      auc: 0,
    },
    trainingData: {
      races: raw?.trainingRaces ?? raw?.trainingData?.races ?? [],
      rows: Number(raw?.trainingRows ?? raw?.trainingData?.rows ?? 0),
      cvMethod: raw?.trainingData?.cvMethod ?? raw?.modelMetrics?.estimators?.[0] ?? "Unknown",
    },
    limitations: raw?.limitations ?? raw?.pitWallNotes ?? [],
    actualResult: actualResult as RacePrediction["actualResult"],
    pitWallNotes: raw?.pitWallNotes ?? [],
  };
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
      number: null,
      headshot: null,
      broadcastName: null,
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
