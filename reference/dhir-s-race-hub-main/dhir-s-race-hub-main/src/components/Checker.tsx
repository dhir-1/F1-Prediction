export function Checker({ size = "md" }: { size?: "sm" | "md" }) {
  return <div className={size === "sm" ? "checker-strip-sm" : "checker-strip"} aria-hidden />;
}
