import { FormEvent, useState } from "react";
import { PilotBanner } from "./PilotBanner";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
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
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    navigate(q ? `/investigations?q=${encodeURIComponent(q)}` : "/investigations");
  }

  return (
    <div className="app-shell v2-app-shell pdf-shell">
      <header className="topbar v2-topbar pdf-topbar">
        <button
          className="pdf-brand-button"
          onClick={() => navigate("/")}
          aria-label="SIGNAL home"
        >
          <span className="pdf-brand-bars" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
          </span>
          <span className="pdf-brand-name">SIGNAL</span>
        </button>

        <nav className="topnav pdf-topnav" aria-label="Primary">
          <NavItem to="/">Overview</NavItem>
          <NavItem to="/investigations">Investigations</NavItem>
          <NavItem to="/watchlist">Watchlist</NavItem>
          <NavItem to="/methodology">Methodology</NavItem>
        </nav>

        <div className="pdf-topbar-tools">
          <form className="pdf-global-search" onSubmit={submitSearch}>
            <SearchIcon />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search stocks, e.g. ANTM, TLKM, BBCA..."
              aria-label="Search stocks"
            />
          </form>

          <button
            className="pdf-bell-button"
            aria-label="Notifications"
            title="Notification feed is not connected in this offline build"
          >
            <BellIcon />
            <span className="pdf-notification-dot" />
          </button>

          <button className="pdf-profile-button" aria-label="Profile">
            <span>AS</span>
            <ChevronIcon />
          </button>
        </div>
      </header>

      <main className="page-container v2-page-container pdf-page-container">
        <PilotBanner />
        <Outlet />
      </main>
    </div>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="10.8" cy="10.8" r="6.3" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="m15.6 15.6 4.1 4.1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.8 9.8a5.2 5.2 0 0 1 10.4 0v3.4l1.5 2.6H5.3l1.5-2.6V9.8Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M10 18.5a2.3 2.3 0 0 0 4 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m8 10 4 4 4-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
