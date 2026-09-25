/**
 * FE.1 通信门面 + 路由 + UI Store 单测
 * run: node --experimental-strip-types tests/js/test_fe_framework.mjs
 */

import assert from "node:assert/strict";
import {
  createApiContext,
  refreshPlatform,
  deviceRegisterPayload,
} from "../../apps/web/src/api/index.ts";
import {
  parseHash,
  buildHash,
  isAppRoute,
} from "../../apps/web/src/hooks/use-router.ts";
import { createRootStores } from "../../apps/web/src/stores/index.ts";
import { FEATURES } from "../../apps/web/src/features/index.ts";
import { UI } from "../../apps/web/src/components/index.ts";

// --- parseHash / buildHash ---
{
  const r = parseHash("#/chat");
  assert.equal(r.route, "chat");
  assert.equal(r.sub, undefined);

  const r2 = parseHash("#/settings/llm");
  assert.equal(r2.route, "settings");
  assert.equal(r2.sub, "llm");

  const r3 = parseHash("#/nope");
  assert.equal(r3.route, "chat"); // 非法路由回落

  const r4 = parseHash("#/tasks?filter=done");
  assert.equal(r4.route, "tasks");
  assert.equal(r4.query.filter, "done");

  assert.equal(buildHash("dsl"), "#/dsl");
  assert.equal(buildHash("settings", "mcp"), "#/settings/mcp");
  assert.equal(buildHash("tasks", undefined, { filter: "running" }), "#/tasks?filter=running");
  assert.equal(isAppRoute("skills"), true);
  assert.equal(isAppRoute("foo"), false);
}

// --- ApiContext ---
{
  const calls = [];
  const fakeFetch = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: true,
      status: 200,
      json: async () => ({ fileId: "f1", name: "a.md", size: 1, mime: "text/markdown", uri: "hub://f1" }),
      text: async () => "",
    };
  };
  const api = createApiContext({
    baseUrl: "",
    restFetch: fakeFetch,
    uploadFetch: fakeFetch,
    width: 1280,
    height: 800,
  });
  assert.ok(api.services.rest);
  assert.ok(api.services.bus);
  assert.ok(api.services.files);
  assert.ok(api.services.llm);
  assert.ok(api.modelChat);
  assert.equal(api.platform.layout, "wide");
  assert.equal(typeof deviceRegisterPayload(api).device_id, "string");

  const ref = await api.services.files.upload({ name: "a.md", type: "text/markdown", size: 1 }, "pc-1");
  assert.equal(ref.fileId, "f1");

  const p2 = refreshPlatform(api, 320, 640);
  assert.equal(p2.layout, "narrow");
  assert.equal(api.platform.layout, "narrow");
}

// --- RootStores / UiStore ---
{
  const stores = createRootStores("sess-fe");
  assert.ok(stores.session);
  assert.ok(stores.tasks);
  assert.ok(stores.agents);
  assert.ok(stores.ui);
  assert.equal(stores.ui.get().route.route, "chat");

  let fired = 0;
  const off = stores.ui.subscribe(() => {
    fired += 1;
  });
  stores.ui.setChatSize("expanded");
  stores.ui.setActivePanel("mcp");
  assert.equal(stores.ui.get().chatSize, "expanded");
  assert.equal(stores.ui.get().activePanel, "mcp");
  assert.ok(fired >= 2);
  off();

  // 无 location 环境下 go 不抛错，且 setRoute 可控
  stores.ui.setRoute(parseHash("#/tasks"));
  assert.equal(stores.ui.get().route.route, "tasks");
}

// --- features / components 契约 ---
{
  assert.ok(FEATURES.length >= 6);
  assert.equal(FEATURES[0].id, "chat");
  assert.equal(UI.skillNodeOn, "ui-skill-node--on");
  assert.ok(UI.glass === undefined); // glass 作为类名常量挂在 panel/card
  assert.ok(UI.panel.includes("glass"));
}

console.log("test_fe_framework: ALL PASS");
