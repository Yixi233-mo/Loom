/**
 * FE.6 性能原语 — 虚拟列表 / memo / 防抖
 * 仅标准库 + React，strip-types 可测。
 */

import * as React from "react";

/** 窗口化列表：只渲染可视区 + overscan 行 */
export function computeWindow(
  total: number,
  itemHeight: number,
  scrollTop: number,
  viewportHeight: number,
  overscan = 4
): { start: number; end: number; offsetY: number; totalHeight: number } {
  const totalHeight = total * itemHeight;
  if (total <= 0 || itemHeight <= 0) {
    return { start: 0, end: 0, offsetY: 0, totalHeight: 0 };
  }
  const rawStart = Math.floor(Math.max(0, scrollTop) / itemHeight);
  const visible = Math.ceil(Math.max(viewportHeight, itemHeight) / itemHeight);
  const start = Math.max(0, rawStart - overscan);
  const end = Math.min(total, rawStart + visible + overscan);
  return { start, end, offsetY: start * itemHeight, totalHeight };
}

export interface VirtualListProps<T> {
  items: T[];
  itemHeight: number;
  height: number;
  overscan?: number;
  className?: string;
  "data-view"?: string;
  renderItem: (item: T, index: number) => unknown;
  keyOf: (item: T, index: number) => string;
}

export function VirtualList<T>(props: VirtualListProps<T>) {
  const [scrollTop, setScrollTop] = React.useState(0);
  const { start, end, offsetY, totalHeight } = computeWindow(
    props.items.length,
    props.itemHeight,
    scrollTop,
    props.height,
    props.overscan ?? 4
  );
  const slice = props.items.slice(start, end);

  return React.createElement(
    "div",
    {
      className: (props.className ?? "") + " ui-vlist",
      "data-view": props["data-view"] ?? "virtual-list",
      "data-window-start": String(start),
      "data-window-end": String(end),
      "data-total": String(props.items.length),
      style: {
        height: props.height + "px",
        overflowY: "auto",
        position: "relative",
      },
      onScroll: (ev: { currentTarget: { scrollTop: number } }) => {
        setScrollTop(ev.currentTarget.scrollTop);
      },
    },
    React.createElement(
      "div",
      {
        className: "ui-vlist-spacer",
        style: { height: totalHeight + "px", position: "relative" },
      },
      React.createElement(
        "div",
        {
          className: "ui-vlist-offset",
          style: { transform: `translateY(${offsetY}px)` },
        },
        slice.map((item, i) =>
          React.createElement(
            React.Fragment,
            { key: props.keyOf(item, start + i) },
            props.renderItem(item, start + i) as any
          )
        )
      )
    )
  );
}

/** props 浅比较 memo（createElement 友好） */
export function memo<T extends (args: any) => any>(fn: T, eq?: (a: any, b: any) => boolean): T {
  const Component = fn as any;
  const Memoized = React.memo(Component, eq ?? shallowEqual);
  Memoized.displayName = `Memo(${Component.displayName || Component.name || "Fn"})`;
  return Memoized as unknown as T;
}

export function shallowEqual(a: any, b: any): boolean {
  if (Object.is(a, b)) return true;
  if (!a || !b) return false;
  const ka = Object.keys(a);
  const kb = Object.keys(b);
  if (ka.length !== kb.length) return false;
  for (const k of ka) {
    if (!Object.is(a[k], b[k])) return false;
  }
  return true;
}

/** 防抖（搜索输入 / resize） */
export function debounce<A extends unknown[]>(
  fn: (...args: A) => void,
  waitMs = 150
): ((...args: A) => void) & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const wrapped = (...args: A) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, waitMs);
  };
  wrapped.cancel = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };
  return wrapped;
}

/** 稳定回调引用，避免 memo 失效 */
export function useEvent<A extends unknown[], R>(
  fn: (...args: A) => R
): (...args: A) => R {
  const ref = React.useRef(fn);
  ref.current = fn;
  return React.useCallback((...args: A) => ref.current(...args), []);
}
