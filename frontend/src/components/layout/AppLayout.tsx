import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  ["/", "Guided Demo"],
  ["/documentation", "Documentation & Verification"],
  ["/review", "Human Review"],
  ["/evaluation", "Evaluation"],
] as const;

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">SYNTHETIC QUALITY GATE</div>
          <h1>Dexter Guard</h1>
        </div>
        <div className="environment-badge" aria-label="Synthetic data only">Synthetic data only</div>
      </header>
      <nav className="sidebar" aria-label="Primary navigation">
        {navigation.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="main-content"><Outlet /></main>
    </div>
  );
}
