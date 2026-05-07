import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prior Auth Agent",
  description:
    "AI agent that produces citation-grounded prior authorization decisions.",
};

const NAV = [
  { href: "/policies", label: "Policies" },
  { href: "/precheck", label: "Pre-check" },
  { href: "/determine", label: "Determine" },
  { href: "/queue", label: "Queue" },
  { href: "/eval", label: "Eval" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-paper font-sans text-ink">
        <header className="sticky top-0 z-30 border-b border-rule/70 bg-paper/85 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-8 py-4">
            <Link href="/" className="flex items-center gap-2.5 text-[15px] font-medium">
              <span aria-hidden className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-ink text-white">
                <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5">
                  <path d="M12 3l8 4v5c0 4.5-3.4 8.5-8 9-4.6-.5-8-4.5-8-9V7l8-4z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                </svg>
              </span>
              Prior Auth Agent
            </Link>
            <nav className="flex gap-7 text-[14px] text-soft">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="hover:text-ink"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-8 py-16">{children}</main>
        <footer className="mx-auto max-w-5xl px-8 pb-16 pt-4 text-xs text-soft">
          Citations are spans into the source policy and chart text. No PHI is
          used by default.
        </footer>
      </body>
    </html>
  );
}
