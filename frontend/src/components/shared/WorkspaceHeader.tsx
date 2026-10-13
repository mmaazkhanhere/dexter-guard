type Props = { eyebrow: string; title: string; description: string };

export function WorkspaceHeader({ eyebrow, title, description }: Props) {
  return <div className="workspace-header"><div className="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{description}</p></div>;
}
