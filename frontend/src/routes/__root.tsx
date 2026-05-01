import type { ReactNode } from "react";
import { HeadContent, Link, Outlet, Scripts, createRootRoute } from "@tanstack/react-router";
import { SakuraOverlay } from "../components/SakuraOverlay";
import { SiteDataProvider } from "@/lib/data";
import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--charcoal)] text-[var(--cream)] px-4">
      <div className="max-w-md text-center">
        <h1 className="font-poster text-8xl text-[var(--redorange)]">404</h1>
        <h2 className="mt-4 font-display text-2xl uppercase tracking-widest">Off Track</h2>
        <p className="mt-2 text-sm opacity-70">This page took the wrong line into Turn 1.</p>
        <div className="mt-6">
          <Link to="/" className="btn-stamp">
            Back to the pit wall
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Dhir's Pit Wall - 2026 F1 Predictions" },
      {
        name: "description",
        content:
          "Vintage racing magazine meets modern F1 prediction. Dhir's Pit Wall covers the 2026 Formula One season.",
      },
      { property: "og:title", content: "Dhir's Pit Wall - 2026 F1 Predictions" },
      { property: "og:description", content: "Vintage racing magazine meets modern F1 prediction." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  return (
    <SiteDataProvider>
      <SakuraOverlay />
      <Outlet />
    </SiteDataProvider>
  );
}
