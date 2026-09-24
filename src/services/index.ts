/**
 * 服务层入口 — REST / 事件总线 / 文件上传。
 */

export { RestClient, type FetchLike, type RequestOptions } from "./rest.ts";
export {
  EventBus,
  type Transport,
  type TransportHandlers,
  type BusMessage,
} from "./event-bus.ts";
export { WsTransport } from "./ws-transport.ts";
export { SseTransport } from "./sse-transport.ts";
export { FileService, type UploadProgress } from "./file-service.ts";
export { LlmApi, type LlmProviderDto } from "./llm-api.ts";
export { ModelChatClient } from "./model-chat.ts";
export { fetchMcpCatalog, callMcpTool, primaryDownloadUrl, type McpCatalogItem, type McpCatalogResponse, type McpToolsCallResult } from "./mcp-tools.ts";

import { RestClient } from "./rest.ts";
import { EventBus } from "./event-bus.ts";
import { FileService } from "./file-service.ts";
import { LlmApi } from "./llm-api.ts";

export interface ServiceLayer {
  rest: RestClient;
  bus: EventBus;
  files: FileService;
  llm: LlmApi;
}

export function createServiceLayer(opts?: {
  baseUrl?: string;
  restFetch?: import("./rest.ts").FetchLike;
  uploadFetch?: import("./file-service.ts").UploadFetch;
}): ServiceLayer {
  const rest = new RestClient(opts?.baseUrl ?? "", opts?.restFetch);
  const bus = new EventBus();
  const files = new FileService(rest, bus, opts?.uploadFetch);
  const llm = new LlmApi(rest);
  return { rest, bus, files, llm };
}
