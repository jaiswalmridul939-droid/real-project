import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Claim What's Yours | Farmer scheme support",
  description: "Find public support schemes for farmers in Maharashtra.",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = { themeColor: "#103c2b" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
