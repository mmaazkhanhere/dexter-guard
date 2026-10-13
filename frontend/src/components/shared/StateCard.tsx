import type { ReactNode } from "react";

type Props = { title: string; children: ReactNode; tone?: "neutral" | "warning" | "error" };

export function StateCard({ title, children, tone = "neutral" }: Props) {
  return <section className={`state-card ${tone}`}><h3>{title}</h3><div>{children}</div></section>;
}
