import { Link, Outlet, createRootRoute } from "@tanstack/react-router";
import { SakuraOverlay } from "../components/SakuraOverlay";
import { SiteDataProvider } from "@/lib/data";

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
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootComponent() {
  return (
    <SiteDataProvider>
      <SakuraOverlay />
      <Outlet />
    </SiteDataProvider>
  );
}
