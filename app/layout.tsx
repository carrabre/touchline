import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Touchline · Your match studio",
  description: "Soccer highlights from the whole match.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg?v=soccer-2",
    shortcut: "/favicon.svg?v=soccer-2",
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
