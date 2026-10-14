type Props = { label: string; className?: string };

export function LoadingIndicator({ label, className = "" }: Props) {
  return <span className={`loading-indicator ${className}`.trim()}><span className="loading-spinner" aria-hidden="true" />{label}</span>;
}
