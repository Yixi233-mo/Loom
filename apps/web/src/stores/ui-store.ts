/**
 * FE.1 UI 状态 — 路由订阅 + 布局/面板偏好（跨端共享语义）。
 */

import { Store } from "../state/store.ts";
import {
  getRoute,
  navigate,
  parseHash,
  type AppRoute,
  type RouteState,
} from "../hooks/use-router.ts";

export type ChatSize = "default" | "expanded";

export interface UiState {
  route: RouteState;
  chatSize: ChatSize;
  activePanel: string | null;
}

export function createUiState(): UiState {
  return {
    route: getRoute(),
    chatSize: "default",
    activePanel: null,
  };
}

export class UiStore extends Store<UiState> {
  static create(): UiStore {
    return new UiStore(createUiState());
  }

  setRoute(next: RouteState): void {
    this.patch({ route: next });
  }

  go(route: AppRoute, sub?: string): void {
    navigate(route, sub);
    this.setRoute(getRoute());
  }

  setChatSize(chatSize: ChatSize): void {
    this.patch({ chatSize });
  }

  setActivePanel(activePanel: string | null): void {
    this.patch({ activePanel });
  }

  /** 浏览器 hash 变化时同步（由 App useEffect 调用） */
  syncFromLocation(hash: string): void {
    this.setRoute(parseHash(hash));
  }
}
