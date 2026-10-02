import { NavLink, Outlet, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getInvestigation } from "../lib/api";
import type { InvestigationDetail } from "../types";
import { StatusBadge } from "./StatusBadge";
import { ContextBadge } from "./ContextBadge";
import { WatchlistButton } from "./WatchlistButton";
import { formatDate } from "../lib/format";

export function WorkspaceShell() {
  const { symbol = "" } = useParams();
  const [detail, setDetail] = useState<InvestigationDetail | null>(null);

  useEffect(() => {
    let alive = true;

    getInvestigation(symbol)
      .then((payload) => {
        if (alive) setDetail(payload);
      })
      .catch(() => {
        if (alive) setDetail(null);
      });

    return () => {
      alive = false;
    };
  }, [symbol]);

  return (
    <>
      <section className="ticker-header card">
        <div className="ticker-header-main">
          <div>
            <div className="ticker-title-row">
              <h1>{symbol.toUpperCase()}</h1>
              {detail && <StatusBadge state={detail.state} />}
            </div>

            <div className="ticker-meta-row">
              <span>
                {detail?.identity.company_name ??
                  detail?.identity.peer_group ??
                  "Market investigation"}
              </span>
              {detail?.context.scope && (
                <ContextBadge scope={detail.context.scope} />
              )}
              <span>
                As of {formatDate(detail?.as_of)}
              </span>
            </div>
          </div>

          <div className="ticker-actions">
            <WatchlistButton symbol={symbol} />
          </div>
        </div>

        <nav className="ticker-tabs" aria-label="Ticker workspace">
          <WorkspaceTab to="summary">Summary</WorkspaceTab>
          <WorkspaceTab to="activity">Market Activity</WorkspaceTab>
          <WorkspaceTab to="context">Context</WorkspaceTab>
          <WorkspaceTab to="history">History</WorkspaceTab>
        </nav>
      </section>

      <Outlet />
    </>
  );
}

function WorkspaceTab({
  to,
  children
}: {
  to: string;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        isActive ? "ticker-tab ticker-tab-active" : "ticker-tab"
      }
    >
      {children}
    </NavLink>
  );
}
