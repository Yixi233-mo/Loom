/**
 * FE.1 React hooks — 与现有 createElement 组件兼容（无 JSX 依赖）。
 */

import * as React from "react";
import {
  getRoute,
  parseHash,
  type RouteState,
} from "./use-router.ts";

export function useForceUpdate(): () => void {
  const [, setTick] = React.useState(0);
  return React.useCallback(() => setTick((t) => t + 1), []);
}

export function useWindowSize(): { width: number; height: number } {
  const [size, setSize] = React.useState(() => ({
    width: typeof window === "undefined" ? 1280 : window.innerWidth,
    height: typeof window === "undefined" ? 800 : window.innerHeight,
  }));
  React.useEffect(() => {
    const onResize = () =>
      setSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", onResize);
    onResize();
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return size;
}

export function useHashRoute(): RouteState {
  const [route, setRoute] = React.useState(() => getRoute());
  React.useEffect(() => {
    const onHash = () => setRoute(parseHash(location.hash));
    window.addEventListener("hashchange", onHash);
    onHash();
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}
