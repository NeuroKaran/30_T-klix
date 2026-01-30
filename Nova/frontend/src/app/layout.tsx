import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Nova - AI Assistant",
  description: "Your intelligent companion with persistent memory",
  keywords: ["AI", "assistant", "chatbot", "memory", "Nova"],
  authors: [{ name: "NeuroKaran" }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gradient-animated`}
      >
        {/* Noise texture overlay for depth */}
        <div className="noise-overlay" aria-hidden="true" />

        {/* Main content */}
        <main className="relative z-10 min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
