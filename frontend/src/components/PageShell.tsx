import { ReactNode } from "react";
import { Checker } from "./Checker";
import { Nav } from "./Nav";
import { Ticker } from "./Ticker";

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--charcoal)]">
      <Ticker />
      <Nav />
      <Checker />
      <main className="w-full bg-[var(--cream)] text-[var(--ink)] relative">
        {children}
      </main>
      <Checker />
      <Footer />
    </div>
  );
}

function Footer() {
  return (
    <footer className="bg-[var(--charcoal)] text-[var(--cream)] py-12 px-6">
      <div className="w-full text-center">
        <h3 className="font-poster text-4xl md:text-6xl text-[var(--redorange)] tracking-wider">
          FORMULA ONE . PREDICTION ARCHIVE
        </h3>
        <div className="mt-6 font-mono text-[11px] tracking-[0.3em] opacity-60 uppercase">
          Dhir&apos;s Pit Wall . 2026
        </div>
      </div>
    </footer>
  );
}
