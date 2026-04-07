import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Synapse-D | Brain Digital Twin Platform",
  description: "Structural MRI-based brain development and degeneration prediction platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
