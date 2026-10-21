import type { Metadata, Viewport } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { SITE_URL } from "@/lib/site";

const geistSans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});
const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"] });

const DESCRIPTION =
  "Tell it what you usually cook. It shows you dishes from around the world that are one step away — written as only what's different.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "One Step",
  description: DESCRIPTION,
  applicationName: "One Step",
  openGraph: {
    siteName: "One Step",
    type: "website",
    title: "One Step",
    description: DESCRIPTION,
  },
  twitter: { card: "summary_large_image" },
  appleWebApp: { capable: true, title: "One Step", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbf8f3" },
    { media: "(prefers-color-scheme: dark)", color: "#1c1814" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background font-sans text-foreground">
        {children}
      </body>
    </html>
  );
}
