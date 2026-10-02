import { NavLink, Outlet } from "react-router-dom";

function NavItem({
  to,
  children
}: {
  to: string;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        isActive ? "nav-link nav-link-active" : "nav-link"
      }
    >
      {children}
    </NavLink>
  );
}

export function AppShell() {
  const viewLabel = import.meta.env.VITE_VIEW_LABEL ?? "Historical Demo";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-group">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-name">SIGNAL</div>
            <div className="brand-subtitle">Market Intelligence</div>
          </div>
        </div>

        <nav className="topnav" aria-label="Primary">
          <NavItem to="/">Overview</NavItem>
          <NavItem to="/investigations">Investigations</NavItem>
          <NavItem to="/watchlist">Watchlist</NavItem>
          <NavItem to="/methodology">Methodology</NavItem>
        </nav>

        <div className="top-actions">
          <span className="view-chip">{viewLabel}</span>
          <div className="avatar">SG</div>
        </div>
      </header>

      <main className="page-container">
        <Outlet />
      </main>
    </div>
  );
}
