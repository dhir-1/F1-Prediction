export type Driver = {
  code: string;
  name: string;
  team: string;
  color: string; // hex
  points: number;
};

export const TEAM_COLORS: Record<string, string> = {
  Ferrari: "#DC0000",
  "Red Bull": "#1E40AF",
  McLaren: "#FF8000",
  Mercedes: "#00D2BE",
  "Aston Martin": "#006F62",
  Alpine: "#0090FF",
  Williams: "#005AFF",
  RB: "#2B4562",
  Sauber: "#52E252",
  Haas: "#B6BABD",
};

export const DRIVERS: Driver[] = [
  { code: "HAM", name: "Lewis Hamilton", team: "Ferrari", color: TEAM_COLORS.Ferrari, points: 87 },
  { code: "LEC", name: "Charles Leclerc", team: "Ferrari", color: TEAM_COLORS.Ferrari, points: 95 },
  { code: "VER", name: "Max Verstappen", team: "Red Bull", color: TEAM_COLORS["Red Bull"], points: 102 },
  { code: "TSU", name: "Yuki Tsunoda", team: "Red Bull", color: TEAM_COLORS["Red Bull"], points: 41 },
  { code: "NOR", name: "Lando Norris", team: "McLaren", color: TEAM_COLORS.McLaren, points: 110 },
  { code: "PIA", name: "Oscar Piastri", team: "McLaren", color: TEAM_COLORS.McLaren, points: 98 },
  { code: "RUS", name: "George Russell", team: "Mercedes", color: TEAM_COLORS.Mercedes, points: 78 },
  { code: "ANT", name: "Andrea Kimi Antonelli", team: "Mercedes", color: TEAM_COLORS.Mercedes, points: 52 },
  { code: "ALO", name: "Fernando Alonso", team: "Aston Martin", color: TEAM_COLORS["Aston Martin"], points: 28 },
  { code: "STR", name: "Lance Stroll", team: "Aston Martin", color: TEAM_COLORS["Aston Martin"], points: 14 },
  { code: "GAS", name: "Pierre Gasly", team: "Alpine", color: TEAM_COLORS.Alpine, points: 22 },
  { code: "DOO", name: "Jack Doohan", team: "Alpine", color: TEAM_COLORS.Alpine, points: 9 },
  { code: "ALB", name: "Alexander Albon", team: "Williams", color: TEAM_COLORS.Williams, points: 31 },
  { code: "SAI", name: "Carlos Sainz", team: "Williams", color: TEAM_COLORS.Williams, points: 36 },
  { code: "LAW", name: "Liam Lawson", team: "RB", color: TEAM_COLORS.RB, points: 12 },
  { code: "HAD", name: "Isack Hadjar", team: "RB", color: TEAM_COLORS.RB, points: 8 },
  { code: "HUL", name: "Nico Hülkenberg", team: "Sauber", color: TEAM_COLORS.Sauber, points: 18 },
  { code: "BOR", name: "Gabriel Bortoleto", team: "Sauber", color: TEAM_COLORS.Sauber, points: 6 },
  { code: "OCO", name: "Esteban Ocon", team: "Haas", color: TEAM_COLORS.Haas, points: 16 },
  { code: "BEA", name: "Oliver Bearman", team: "Haas", color: TEAM_COLORS.Haas, points: 11 },
  { code: "COL", name: "Franco Colapinto", team: "Alpine", color: TEAM_COLORS.Alpine, points: 4 },
  { code: "ZHO", name: "Zhou Guanyu", team: "Sauber", color: TEAM_COLORS.Sauber, points: 3 },
];

export type Race = {
  round: number;
  name: string;
  country: string;
  flag: string;
  circuit: string;
  date: string; // ISO
  laps: number;
  lengthKm: number;
  status: "completed" | "next" | "upcoming";
  winner?: string;
  podium?: [string, string, string];
  fastestLap?: string;
};

export const RACES: Race[] = [
  { round: 1, name: "Australian Grand Prix", country: "Australia", flag: "🇦🇺", circuit: "Albert Park", date: "2026-03-08", laps: 58, lengthKm: 5.278, status: "completed", winner: "HAM", podium: ["HAM", "VER", "NOR"], fastestLap: "HAM" },
  { round: 2, name: "Chinese Grand Prix", country: "China", flag: "🇨🇳", circuit: "Shanghai International", date: "2026-03-22", laps: 56, lengthKm: 5.451, status: "completed", winner: "NOR", podium: ["NOR", "PIA", "LEC"], fastestLap: "PIA" },
  { round: 3, name: "Japanese Grand Prix", country: "Japan", flag: "🇯🇵", circuit: "Suzuka", date: "2026-04-05", laps: 53, lengthKm: 5.807, status: "completed", winner: "VER", podium: ["VER", "NOR", "HAM"], fastestLap: "VER" },
  { round: 4, name: "Saudi Arabian Grand Prix", country: "Saudi Arabia", flag: "🇸🇦", circuit: "Jeddah Corniche", date: "2026-04-19", laps: 50, lengthKm: 6.174, status: "completed", winner: "HAM", podium: ["HAM", "LEC", "RUS"], fastestLap: "HAM" },
  { round: 5, name: "Bahrain Grand Prix", country: "Bahrain", flag: "🇧🇭", circuit: "Sakhir", date: "2026-04-26", laps: 57, lengthKm: 5.412, status: "completed", winner: "LEC", podium: ["LEC", "PIA", "VER"], fastestLap: "LEC" },
  { round: 6, name: "Miami Grand Prix", country: "USA", flag: "🇺🇸", circuit: "Miami International Autodrome", date: "2026-05-04", laps: 57, lengthKm: 5.412, status: "next" },
  { round: 7, name: "Emilia Romagna GP", country: "Italy", flag: "🇮🇹", circuit: "Imola", date: "2026-05-17", laps: 63, lengthKm: 4.909, status: "upcoming" },
  { round: 8, name: "Monaco Grand Prix", country: "Monaco", flag: "🇲🇨", circuit: "Circuit de Monaco", date: "2026-05-24", laps: 78, lengthKm: 3.337, status: "upcoming" },
  { round: 9, name: "Spanish Grand Prix", country: "Spain", flag: "🇪🇸", circuit: "Catalunya", date: "2026-06-07", laps: 66, lengthKm: 4.657, status: "upcoming" },
  { round: 10, name: "Canadian Grand Prix", country: "Canada", flag: "🇨🇦", circuit: "Gilles Villeneuve", date: "2026-06-14", laps: 70, lengthKm: 4.361, status: "upcoming" },
  { round: 11, name: "Austrian Grand Prix", country: "Austria", flag: "🇦🇹", circuit: "Red Bull Ring", date: "2026-06-28", laps: 71, lengthKm: 4.318, status: "upcoming" },
  { round: 12, name: "British Grand Prix", country: "UK", flag: "🇬🇧", circuit: "Silverstone", date: "2026-07-05", laps: 52, lengthKm: 5.891, status: "upcoming" },
  { round: 13, name: "Hungarian Grand Prix", country: "Hungary", flag: "🇭🇺", circuit: "Hungaroring", date: "2026-07-26", laps: 70, lengthKm: 4.381, status: "upcoming" },
  { round: 14, name: "Belgian Grand Prix", country: "Belgium", flag: "🇧🇪", circuit: "Spa-Francorchamps", date: "2026-08-02", laps: 44, lengthKm: 7.004, status: "upcoming" },
  { round: 15, name: "Dutch Grand Prix", country: "Netherlands", flag: "🇳🇱", circuit: "Zandvoort", date: "2026-08-23", laps: 72, lengthKm: 4.259, status: "upcoming" },
  { round: 16, name: "Italian Grand Prix", country: "Italy", flag: "🇮🇹", circuit: "Monza", date: "2026-09-06", laps: 53, lengthKm: 5.793, status: "upcoming" },
  { round: 17, name: "Azerbaijan GP", country: "Azerbaijan", flag: "🇦🇿", circuit: "Baku City", date: "2026-09-20", laps: 51, lengthKm: 6.003, status: "upcoming" },
  { round: 18, name: "Singapore GP", country: "Singapore", flag: "🇸🇬", circuit: "Marina Bay", date: "2026-10-04", laps: 62, lengthKm: 4.940, status: "upcoming" },
  { round: 19, name: "United States GP", country: "USA", flag: "🇺🇸", circuit: "Circuit of the Americas", date: "2026-10-25", laps: 56, lengthKm: 5.513, status: "upcoming" },
  { round: 20, name: "Mexico City GP", country: "Mexico", flag: "🇲🇽", circuit: "Hermanos Rodríguez", date: "2026-11-01", laps: 71, lengthKm: 4.304, status: "upcoming" },
  { round: 21, name: "São Paulo GP", country: "Brazil", flag: "🇧🇷", circuit: "Interlagos", date: "2026-11-08", laps: 71, lengthKm: 4.309, status: "upcoming" },
  { round: 22, name: "Las Vegas GP", country: "USA", flag: "🇺🇸", circuit: "Las Vegas Strip", date: "2026-11-21", laps: 50, lengthKm: 6.201, status: "upcoming" },
  { round: 23, name: "Qatar Grand Prix", country: "Qatar", flag: "🇶🇦", circuit: "Lusail", date: "2026-11-29", laps: 57, lengthKm: 5.419, status: "upcoming" },
  { round: 24, name: "Abu Dhabi GP", country: "UAE", flag: "🇦🇪", circuit: "Yas Marina", date: "2026-12-06", laps: 58, lengthKm: 5.281, status: "upcoming" },
];

export const driverByCode = (c: string) => DRIVERS.find(d => d.code === c)!;

export const standings = () => [...DRIVERS].sort((a, b) => b.points - a.points);

export const constructorStandings = () => {
  const map = new Map<string, { team: string; color: string; points: number }>();
  for (const d of DRIVERS) {
    const e = map.get(d.team) ?? { team: d.team, color: d.color, points: 0 };
    e.points += d.points;
    map.set(d.team, e);
  }
  return [...map.values()].sort((a, b) => b.points - a.points);
};

// Miami prediction
export const MIAMI_PREDICTION = {
  podium: [
    { code: "NOR", confidence: 68 },
    { code: "VER", confidence: 54 },
    { code: "HAM", confidence: 47 },
  ],
  grid: [
    "NOR","VER","HAM","LEC","PIA","RUS","SAI","ALO","ANT","TSU",
    "ALB","GAS","HUL","OCO","STR","LAW","BEA","HAD","BOR","DOO","COL","ZHO"
  ] as string[],
  podiumProb: {
    NOR: 88, VER: 81, HAM: 74, LEC: 69, PIA: 65, RUS: 51, SAI: 38,
    ALO: 30, ANT: 27, TSU: 22, ALB: 18, GAS: 15, HUL: 12, OCO: 10,
    STR: 8, LAW: 6, BEA: 5, HAD: 4, BOR: 3, DOO: 3, COL: 2, ZHO: 2,
  } as Record<string, number>,
  features: [
    { name: "Grid Position", weight: 92 },
    { name: "Recent Form (3R)", weight: 71 },
    { name: "Team Pace Index", weight: 64 },
    { name: "Quali Delta", weight: 58 },
    { name: "Tyre Strategy", weight: 49 },
    { name: "Track History", weight: 41 },
    { name: "Driver Rating", weight: 36 },
    { name: "DNF Risk", weight: 28 },
    { name: "Weather Score", weight: 22 },
    { name: "Pit Stop Avg", weight: 18 },
    { name: "Sector 2 Pace", weight: 14 },
    { name: "Car Upgrades", weight: 10 },
  ],
  metrics: { f1: 0.857, precision: 0.750, recall: 1.000, auc: 0.968 },
};
