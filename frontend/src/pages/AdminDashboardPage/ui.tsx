import { type ButtonHTMLAttributes, type ReactNode } from "react";

/* Building blocks for the admin dashboard, in the student dashboard's style
 * (the colour tokens in index.css). */

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-line bg-surface p-6 ${className}`}
    >
      {children}
    </div>
  );
}

const BADGE_TONES = {
  neutral: "bg-line text-ink",
  active: "bg-blue/20 text-ink",
  inactive: "bg-pink/15 text-pink",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: keyof typeof BADGE_TONES;
}) {
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-medium ${BADGE_TONES[tone]}`}
    >
      {children}
    </span>
  );
}

const BUTTON_VARIANTS = {
  primary: "bg-blue text-white hover:bg-blue/90",
  quiet: "border border-line text-ink hover:border-slate",
};

export function Button({
  variant = "quiet",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof BUTTON_VARIANTS;
}) {
  return (
    <button
      type="button"
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

// Scrolls sideways on narrow screens instead of squashing the columns.
export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">{children}</table>
    </div>
  );
}

export function Th({ children }: { children?: ReactNode }) {
  return (
    <th className="border-b border-line px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate">
      {children}
    </th>
  );
}

export function Td({
  children,
  className = "",
}: {
  children?: ReactNode;
  className?: string;
}) {
  return (
    <td className={`border-b border-line px-3 py-3 text-ink ${className}`}>
      {children}
    </td>
  );
}
