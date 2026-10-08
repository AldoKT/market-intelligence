import "./product-design.css";
import {MarketTicker} from "./components/MarketTicker";
import "./fixed-chrome.css";
import {
  Navigate,
  RouterProvider,
  useLocation,
  createHashRouter,
  createBrowserRouter
} from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { WorkspaceShell } from "./components/WorkspaceShell";
import { InvestigationsPage } from "./pages/InvestigationsPage";
import { HistoryDesignPage } from "./pages/HistoryDesignPage";
import { WatchlistPage } from "./pages/WatchlistPage";
import { MethodologyPage } from "./pages/MethodologyPage";

import "./broker.css";

import { lazy, Suspense, useEffect, useLayoutEffect, useRef } from "react";
const OverviewMockupsPage = lazy(() => import("./pages/OverviewMockupsPage").then(m => ({default: m.OverviewMockupsPage})));

const SummaryMockupsPage = lazy(() => import("./pages/SummaryMockupsPage").then(m => ({default: m.SummaryMockupsPage})));

const ActivityMockupsPage = lazy(() => import("./pages/ActivityMockupsPage").then(m => ({default: m.ActivityMockupsPage})));

const BrokerMockupsPage = lazy(() => import("./pages/BrokerMockupsPage").then(m => ({default: m.BrokerMockupsPage})));

const BrokerReferencePage = lazy(() => import("./pages/BrokerReferencePage").then(m => ({default: m.BrokerReferencePage})));
const ContextDesignPage = lazy(() => import("./pages/ContextDesignPage").then(m => ({default:m.ContextDesignPage})));
function ProductPage({children}:{children:React.ReactNode}){const {pathname}=useLocation();useLayoutEffect(()=>{const previous=window.history.scrollRestoration;window.history.scrollRestoration="manual";window.scrollTo({top:0,left:0,behavior:"instant"});return()=>{window.history.scrollRestoration=previous;};},[pathname]);const root=useRef<HTMLDivElement>(null);useEffect(()=>{const host=root.current;if(!host)return;let resize:ResizeObserver|undefined;let observed:HTMLElement|null=null;const bind=()=>{const nav=host.querySelector<HTMLElement>(".ov-glass-nav");if(!nav||nav===observed)return;resize?.disconnect();observed=nav;const measure=()=>{const height=nav.getBoundingClientRect().height;if(height>0)host.style.setProperty("--signal-nav-height",height+"px");};measure();resize=new ResizeObserver(measure);resize.observe(nav);};const mutation=new MutationObserver(bind);mutation.observe(host,{childList:true,subtree:true});bind();return()=>{mutation.disconnect();resize?.disconnect();};},[]);return <div ref={root} className="product-page">{children}<MarketTicker/></div>;}
const router = (import.meta.env.VITE_STATIC_DEMO === "true" ? createHashRouter : createBrowserRouter)([
 {path:"/",element:<ProductPage><Suspense fallback={<p>Memuat SIGNAL…</p>}><OverviewMockupsPage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/summary",element:<ProductPage><Suspense fallback={<p>Memuat Summary…</p>}><SummaryMockupsPage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/activity",element:<ProductPage><Suspense fallback={<p>Memuat Activity…</p>}><ActivityMockupsPage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/brokers",element:<ProductPage><Suspense fallback={<p>Memuat Broker…</p>}><BrokerReferencePage/></Suspense></ProductPage>},
 {path:"/investigations/:symbol/context",element:<ProductPage><Suspense fallback={<p>Memuat Context…</p>}><ContextDesignPage/></Suspense></ProductPage>},
 {path:"/methodology",element:<ProductPage><MethodologyPage/></ProductPage>},
 {path:"/watchlist",element:<ProductPage><WatchlistPage/></ProductPage>},
 {path:"/investigations",element:<ProductPage><InvestigationsPage/></ProductPage>},
 {path:"/investigations/:symbol/history",element:<ProductPage><HistoryDesignPage/></ProductPage>},
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
        path: "investigations/:symbol",
        element: <WorkspaceShell />,
        children: [
          {
            index: true,
            element: <Navigate to="summary" replace />
          },

        ]
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
