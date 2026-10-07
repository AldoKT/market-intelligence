import "./product-design.css";
import {
  Navigate,
  RouterProvider,
  createBrowserRouter
} from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { WorkspaceShell } from "./components/WorkspaceShell";
import { InvestigationsPage } from "./pages/InvestigationsPage";
import { HistoryPage } from "./pages/HistoryPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { MethodologyPage } from "./pages/MethodologyPage";

import "./broker.css";

import { lazy, Suspense } from "react";
const OverviewMockupsPage = lazy(() => import("./pages/OverviewMockupsPage").then(m => ({default: m.OverviewMockupsPage})));

const SummaryMockupsPage = lazy(() => import("./pages/SummaryMockupsPage").then(m => ({default: m.SummaryMockupsPage})));

const ActivityMockupsPage = lazy(() => import("./pages/ActivityMockupsPage").then(m => ({default: m.ActivityMockupsPage})));

const BrokerMockupsPage = lazy(() => import("./pages/BrokerMockupsPage").then(m => ({default: m.BrokerMockupsPage})));

const BrokerReferencePage = lazy(() => import("./pages/BrokerReferencePage").then(m => ({default: m.BrokerReferencePage})));
const ContextDesignPage = lazy(() => import("./pages/ContextDesignPage").then(m => ({default:m.ContextDesignPage})));
function ProductPage({children}:{children:React.ReactNode}){return <div className="product-page">{children}</div>;}
const router = createBrowserRouter([
 {path:"/",element:<ProductPage><Suspense fallback={<p>Memuat SIGNAL…</p>}><OverviewMockupsPage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/summary",element:<ProductPage><Suspense fallback={<p>Memuat Summary…</p>}><SummaryMockupsPage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/activity",element:<ProductPage><Suspense fallback={<p>Memuat Activity…</p>}><ActivityMockupsPage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/brokers",element:<ProductPage><Suspense fallback={<p>Memuat Broker…</p>}><BrokerReferencePage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/context",element:<ProductPage><Suspense fallback={<p>Memuat Context…</p>}><ContextDesignPage/></Suspense></ProductPage>},
 {path:"/design/context",element:<Suspense fallback={<p>Memuat Context…</p>}><ContextDesignPage /></Suspense>},
 {path:"/design/brokers/reference",element:<Suspense fallback={<p>Memuat Broker…</p>}><BrokerReferencePage /></Suspense>},
  {path:"/design/brokers",element:<Suspense fallback={<p>Memuat konsep Broker…</p>}><BrokerMockupsPage /></Suspense>},
  { path: "/design/activity", element: <Suspense fallback={<p>Memuat konsep Market Activity…</p>}><ActivityMockupsPage /></Suspense> },
  { path: "/design/summary", element: <Suspense fallback={<p>Memuat konsep Summary…</p>}><SummaryMockupsPage /></Suspense> },
  { path: "/design/overview", element: <Suspense fallback={<p>Memuat konsep Overview…</p>}><OverviewMockupsPage /></Suspense> },
  {
    element: <AppShell />,
    children: [
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
