import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Prior Authorization Agent",
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
      <body className="min-h-screen font-sans">
        <header className="border-b border-line bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <Link href="/" className="text-base font-semibold tracking-tight">
              Prior Auth Agent
            </Link>
            <nav className="flex gap-5 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-slate-600 hover:text-ink"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-8 text-xs text-slate-500">
          Built with Claude. Citations are spans into the source policy and
          chart text. No PHI is used by default.
        </footer>
      </body>
    </html>
  );
}
