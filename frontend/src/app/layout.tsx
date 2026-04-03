import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Synapse-D | Brain Digital Twin",
  description: "Structural MRI-based brain development and degeneration prediction platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ margin: 0, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
