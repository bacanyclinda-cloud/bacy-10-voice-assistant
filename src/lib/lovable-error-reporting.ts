type LovableErrorOptions = {
  mechanism?: "manual" | "onerror" | "unhandledrejection" | "react_error_boundary";
  handled?: boolean;
  severity?: "error" | "warning" | "info";
};

type LovableEvents = {
  track?: (event: string, properties?: Record<string, unknown>) => string | null;
  captureException?: (
    error: unknown,
    context?: Record<string, unknown>,
    options?: LovableErrorOptions,
  ) => void;
};

declare global {
  interface Window {
    __lovableEvents?: LovableEvents;
    __lovableReportRuntimeError?: (payload: {
      message: string;
      stack?: string;
      filename?: string;
    }) => void;
  }
}

export function reportLovableError(error: unknown, context: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  const safeMessage = redactSensitiveText(describeThrown(error)).slice(0, MAX_SERIALIZED_LENGTH);
  const safeError = new Error(safeMessage);
  const originalStack = error instanceof Error ? error.stack : undefined;
  if (originalStack) safeError.stack = redactSensitiveText(originalStack).slice(0, 8000);
  const safeContext = Object.fromEntries(Object.entries(context)
    .filter(([key]) => !/(?:authorization|token|secret|password|api.?key|email|phone|body|payload)/i.test(key))
    .map(([key, value]) => [key, typeof value === "string"
      ? redactSensitiveText(value).slice(0, 500)
      : (typeof value === "number" || typeof value === "boolean" ? value : "[omitted]")]));
  window.__lovableEvents?.captureException?.(
    safeError,
    {
      source: "react_error_boundary",
      route: window.location.pathname,
      ...safeContext,
    },
    {
      mechanism: "react_error_boundary",
      handled: false,
      severity: "error",
    },
  );
  // Prod React does not rethrow boundary-caught errors to window.onerror, so the
  // editor's telemetry never sees them. Forward to lovable.js's reporting hook,
  // which is present only inside the editor preview.
  const stack = safeError.stack;
  window.__lovableReportRuntimeError?.({
    message: safeMessage,
    ...(stack !== undefined && { stack }),
    filename: window.location.pathname,
  });
}

const MAX_SERIALIZED_LENGTH = 2000;

function redactSensitiveText(value: string): string {
  return value
    .replace(/(?:authorization|access[_ -]?token|refresh[_ -]?token|api[_ -]?key|client[_ -]?secret|password|passphrase)\\s*[:=]\\s*["']?[^\\s"'&,;]+/gi, "[REDACTED_SECRET]")
    .replace(/\\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\\b/g, "[REDACTED_API_KEY]")
    .replace(/\\bgh[pousr]_[A-Za-z0-9]{20,}\\b/g, "[REDACTED_GITHUB_TOKEN]")
    .replace(/\\bAIza[0-9A-Za-z_-]{30,}\\b/g, "[REDACTED_GOOGLE_KEY]")
    .replace(/\\bAKIA[0-9A-Z]{16}\\b/g, "[REDACTED_AWS_KEY]")
    .replace(/\\bBearer\\s+[A-Za-z0-9._~+\\/-]{20,}/gi, "Bearer [REDACTED]")
    .replace(/\\beyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\b/g, "[REDACTED_JWT]")
    .replace(/\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}\\b/gi, "[REDACTED_EMAIL]")
    .replace(/\\+?\\d[\\d\\s().-]{7,}\\d/g, "[REDACTED_NUMBER]");
}

// Loaders and server fns throw raw Responses and plain objects (a Supabase
// `{ message, code, details }`), which String() reduces to "[object ...]".
function describeThrown(error: unknown): string {
  if (error instanceof Response) {
    return `Response ${error.status}${error.url ? ` at ${error.url}` : ""}`;
  }
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  const { message } = (error ?? {}) as { message?: unknown };
  if (typeof message === "string" && message.length > 0) return message;
  try {
    return JSON.stringify(error)?.slice(0, MAX_SERIALIZED_LENGTH) ?? String(error);
  } catch {
    return String(error);
  }
}
