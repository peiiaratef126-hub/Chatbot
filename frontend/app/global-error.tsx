"use client";

import * as Sentry from "@sentry/nextjs";
import NextError from "next/error";
import { useEffect } from "react";

export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-[#0b0f19] text-white flex min-h-screen items-center justify-center">
        <div className="text-center p-8 rounded-xl border border-red-500/20 bg-red-950/20 max-w-md">
          <h2 className="text-xl font-bold text-red-400 mb-2">Something went wrong!</h2>
          <p className="text-sm text-gray-400 mb-4">
            An unexpected error has been captured and reported to Sentry.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-500/80 hover:bg-red-500 text-white rounded-lg text-sm transition"
          >
            Reload application
          </button>
        </div>
      </body>
    </html>
  );
}
