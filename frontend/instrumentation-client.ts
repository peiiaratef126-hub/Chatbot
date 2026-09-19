import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn:
    process.env.NEXT_PUBLIC_SENTRY_DSN ||
    "https://58894e228d938c5bd3e84f6b992d2720@o4512106311712768.ingest.de.sentry.io/4512106423255120",
  tracesSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  enableLogs: true,
  integrations: [
    Sentry.replayIntegration(),
  ],
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
