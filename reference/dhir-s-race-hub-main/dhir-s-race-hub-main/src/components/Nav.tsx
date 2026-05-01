import { Link } from "@tanstack/react-router";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/prediction", label: "Prediction" },
  { to: "/history", label: "Race History" },
  { to: "/about", label: "About" },
] as const;

export function Nav() {
  return (
    <nav className="bg-[var(--charcoal)] text-[var(--cream)] border-b border-white/10">
      <div className="max-w-[1280px] mx-auto px-6 py-3 flex items-center justify-between gap-6 flex-wrap">
        <Link to="/" className="font-poster text-2xl tracking-wider">
          DHIR'S <span className="text-[var(--redorange)] italic">PIT WALL</span>
        </Link>
        <div className="flex items-center gap-1 flex-wrap">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={{ exact: l.to === "/" }}
              activeProps={{
                className:
                  "bg-[var(--redorange)] text-white",
              }}
              inactiveProps={{
                className: "hover:bg-white/10",
              }}
              className="px-4 py-2 text-[11px] font-semibold tracking-[0.2em] uppercase font-sans transition-colors"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
