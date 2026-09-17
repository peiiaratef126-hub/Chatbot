import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Customer Support RAG Chatbot | Portfolio Edition",
  description: "End-to-End Zero-Cost Customer Support Agentic RAG System powered by Groq Cloud, Qdrant, and Next.js.",
  keywords: ["RAG", "Chatbot", "Customer Support", "Groq", "Llama 3.1", "Qdrant", "Next.js"],
  authors: [{ name: "LoneVertex" }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚡</text></svg>" />
      </head>
      <body className="min-h-[100dvh] flex flex-col bg-background text-foreground transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
