import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Touchline · Your match studio",
  description: "Private soccer highlights from the whole match.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
