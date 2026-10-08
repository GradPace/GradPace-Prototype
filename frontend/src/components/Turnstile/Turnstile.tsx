import { useEffect, useRef } from "react";

// Cloudflare Turnstile widget (bot check on login/signup). The backend
// verifies the token it produces - see backend/accounts/turnstile.py.
//
// Tokens are single-use: after a failed submit, remount this component (bump
// its `key`) to get a fresh challenge.

const SCRIPT_SRC =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

type TurnstileOptions = {
  sitekey: string;
  action: string;
  callback: (token: string) => void;
  "expired-callback": () => void;
  "error-callback": () => void;
};

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, options: TurnstileOptions) => string;
      remove: (widgetId: string) => void;
    };
  }
}

// Shared across every widget on the page - the script only loads once.
let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_SRC;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null; // allow a retry on the next mount
        reject(new Error("Failed to load Turnstile"));
      };
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

type Props = {
  // Must match what the backend expects for this form ('login'/'register').
  action: string;
  // Called with a token once the challenge passes, and with null when it
  // expires or errors, so the form can disable submit until it's valid again.
  onToken: (token: string | null) => void;
};

export default function Turnstile({ action, onToken }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Latest onToken without re-rendering the widget whenever the parent
  // passes a new function.
  const onTokenRef = useRef(onToken);
  useEffect(() => {
    onTokenRef.current = onToken;
  });

  useEffect(() => {
    let widgetId: string | undefined;
    let cancelled = false;

    loadScript()
      .then(() => {
        if (cancelled || !containerRef.current || !window.turnstile) return;
        widgetId = window.turnstile.render(containerRef.current, {
          sitekey: import.meta.env.VITE_TURNSTILE_SITE_KEY,
          action,
          callback: (token) => onTokenRef.current(token),
          "expired-callback": () => onTokenRef.current(null),
          "error-callback": () => onTokenRef.current(null),
        });
      })
      .catch(() => onTokenRef.current(null));

    return () => {
      cancelled = true;
      if (widgetId) window.turnstile?.remove(widgetId);
    };
  }, [action]);

  return <div ref={containerRef} />;
}
