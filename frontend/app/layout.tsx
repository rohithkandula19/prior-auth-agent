import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prior Auth Agent",
  description:
    "AI agent that produces citation-grounded prior authorization decisions.",
};

const NAV = [
  { href: "/", label: "Home" },
  { href: "/policies", label: "Policies" },
  { href: "/determine", label: "Determine" },
  { href: "/eval", label: "Eval" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased text-ink">
        <header className="border-b border-line/70 bg-white/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
              <span aria-hidden className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-ink text-white">
                <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5">
                  <path d="M12 3l8 4v5c0 4.5-3.4 8.5-8 9-4.6-.5-8-4.5-8-9V7l8-4z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
                </svg>
              </span>
              Prior Auth Agent
            </Link>
            <nav className="flex gap-7 text-[14px]">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-slate-500 hover:text-ink"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-12">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 pb-12 pt-4 text-xs text-slate-400">
          Citations are spans into the source policy and chart text. No PHI is used by default.
        </footer>
      </body>
    </html>
  );
}
