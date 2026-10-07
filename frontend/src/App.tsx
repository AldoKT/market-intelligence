import {
  Navigate,
  RouterProvider,
  createBrowserRouter
} from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { WorkspaceShell } from "./components/WorkspaceShell";
import { OverviewPage } from "./pages/OverviewPage";
import { InvestigationsPage } from "./pages/InvestigationsPage";
import { SummaryPage } from "./pages/SummaryPage";
import { ActivityPage } from "./pages/ActivityPage";
import { ContextPage } from "./pages/ContextPage";
import { HistoryPage } from "./pages/HistoryPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { MethodologyPage } from "./pages/MethodologyPage";

import { BrokersPage } from "./pages/BrokersPage";
import "./broker.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <OverviewPage />
      },
      {
        path: "investigations",
        element: <InvestigationsPage />
      },
      {
        path: "investigations/:symbol",
        element: <WorkspaceShell />,
        children: [
          {
            index: true,
            element: <Navigate to="summary" replace />
          },
          {
            path: "summary",
            element: <SummaryPage />
          },
          {
            path: "activity",
            element: <ActivityPage />
          },
          {
            path: "context",
            element: <ContextPage />
          },
          {
            path: "brokers",
            element: <BrokersPage />
          },
          {
            path: "history",
            element: <HistoryPage />
          }
        ]
      },
      {
        path: "watchlist",
        element: <WatchlistPage />
      },
      {
        path: "methodology",
        element: <MethodologyPage />
      },
      {
        path: "*",
        element: <Navigate to="/" replace />
      }
    ]
  }
]);

export default function App() {
  return <RouterProvider router={router} />;
}
