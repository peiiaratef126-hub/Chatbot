/**
 * Canonical brand definitions, regex patterns, and timeouts for SupportRAG.
 */

export const SUPPORTED_BRANDS = [
  "AppleSupport",
  "AmazonHelp",
  "Uber_Support",
  "SpotifyCares",
  "Delta",
  "NikeSupport",
] as const;

export type SupportedBrand = (typeof SUPPORTED_BRANDS)[number];

export const ALL_BRANDS_FILTER = [
  "All Brands",
  ...SUPPORTED_BRANDS,
] as const;

export type BrandFilter = (typeof ALL_BRANDS_FILTER)[number];

export const GREETING_REGEX =
  /^(\s*)*(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|yo|howdy)(\s+(there|friend|team|support|everyone))?(\s*|[!?.])*$/i;

export const ORDER_TRACKING_REGEX =
  /(?:order|tracking|pkg|shipment)\s*(?:#|id|number)?\s*[:#\-]?\s*([A-Za-z0-9\-_]{4,})|#([A-Za-z0-9\-_]{4,})/i;

export const ESCALATION_REGEX =
  /speak to (a )?human|talk to (a )?human|human (supervisor|agent|representative|specialist)|supervisor|real person|fraud|unacceptable|lawsuit|manager|demanding a human/i;

export const DEFAULT_FETCH_TIMEOUT_MS = 10000;
export const GROQ_FETCH_TIMEOUT_MS = 15000;
