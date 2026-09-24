/**
 * FE.1 通用 hooks 入口。
 */

export {
  parseHash,
  buildHash,
  navigate,
  getRoute,
  isAppRoute,
  type AppRoute,
  type RouteState,
} from "./use-router.ts";

export { useForceUpdate, useWindowSize, useHashRoute } from "./use-react-hooks.ts";
