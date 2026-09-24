/**
 * FE.1 轻量 hash 路由 — 不引入 React Router。
 * 路径形如 `#/chat` `#/tasks` `#/files` `#/settings/llm` `#/dsl` `#/skills`。
 */

export type AppRoute =
  | "chat"
  | "tasks"
  | "files"
  | "settings"
  | "dsl"
  | "skills";

export interface RouteState {
  path: string;
  route: AppRoute;
  sub?: string;
  query: Record<string, string>;
}

const DEFAULT_ROUTE: AppRoute = "chat";

const VALID_ROUTES: readonly AppRoute[] = [
  "chat",
  "tasks",
  "files",
  "settings",
  "dsl",
  "skills",
];

export function isAppRoute(v: string): v is AppRoute {
  return (VALID_ROUTES as readonly string[]).includes(v);
}

export function parseHash(hash: string): RouteState {
  const raw = (hash || "").replace(/^#\/?/, "");
  const [pathPart, queryPart] = raw.split("?");
  const segments = (pathPart || "").split("/").filter(Boolean);
  const head = segments[0] ?? DEFAULT_ROUTE;
  const route: AppRoute = isAppRoute(head) ? head : DEFAULT_ROUTE;
  const sub = segments[1];
  const query: Record<string, string> = {};
  if (queryPart) {
    for (const pair of queryPart.split("&")) {
      if (!pair) continue;
      const [k, v = ""] = pair.split("=");
      query[decodeURIComponent(k)] = decodeURIComponent(v);
    }
  }
  return {
    path: `#/${segments.join("/")}`,
    route,
    sub,
    query,
  };
}

export function buildHash(route: AppRoute, sub?: string, query?: Record<string, string>): string {
  const segs: string[] = [route];
  if (sub) segs.push(sub);
  let h = `#/${segs.join("/")}`;
  if (query && Object.keys(query).length > 0) {
    const qs = Object.entries(query)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
    h += `?${qs}`;
  }
  return h;
}

export function navigate(
  route: AppRoute,
  sub?: string,
  query?: Record<string, string>
): void {
  if (typeof location === "undefined") return;
  location.hash = buildHash(route, sub, query);
}

export function getRoute(): RouteState {
  if (typeof location === "undefined") {
    return parseHash("");
  }
  return parseHash(location.hash);
}
