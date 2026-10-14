import type { ReactNode } from "react";

type Props = { title: string; description?: string; children: ReactNode; tone?: "neutral" | "warning" | "error" };

export function StateCard({ title, description, children, tone = "neutral" }: Props) {
  return <section className={`state-card ${tone}`}><h3>{title}</h3>{description && <p className="state-card-description">{description}</p>}<div>{children}</div></section>;
}
