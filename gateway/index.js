/**
 * OpenClaw Gateway — 最小化消息转发网关
 *
 * 接收来自 WhatsApp (Baileys) 和 Telegram (grammY) 的消息，
 * 通过 WebSocket 转发给 AI Parenting 后端，并将回复推送回渠道用户。
 *
 * 同时支持 HTTP Webhook 方式将入站消息 POST 到后端。
 *
 * 环境变量：
 * - OPENCLAW_WS_PORT: WebSocket 端口（默认 8765）
 * - OPENCLAW_PORT: HTTP 管理端口（默认 18789）
 * - OPENCLAW_API_KEY: API 认证密钥
 * - WHATSAPP_ENABLED: 启用 WhatsApp (true/false)
 * - TELEGRAM_ENABLED: 启用 Telegram (true/false)
 * - TELEGRAM_BOT_TOKEN: Telegram Bot Token
 * - WEBHOOK_URL: 后端 Webhook URL
 * - WEBHOOK_SECRET: Webhook 签名密钥
 */

const http = require("http");
const crypto = require("crypto");

const WS_PORT = parseInt(process.env.OPENCLAW_WS_PORT || "8765", 10);
const HTTP_PORT = parseInt(process.env.OPENCLAW_PORT || "18789", 10);
const API_KEY = process.env.OPENCLAW_API_KEY || "";
const WEBHOOK_URL = process.env.WEBHOOK_URL || "";
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || "";

// ---------------------------------------------------------------------------
// HTTP 管理服务（健康检查 + 状态查询）
// ---------------------------------------------------------------------------

const httpServer = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        status: "ok",
        uptime: process.uptime(),
        channels: {
          whatsapp: process.env.WHATSAPP_ENABLED === "true",
          telegram: process.env.TELEGRAM_ENABLED === "true",
        },
      })
    );
    return;
  }

  if (req.url === "/status") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ws_port: WS_PORT,
        http_port: HTTP_PORT,
        webhook_url: WEBHOOK_URL ? "configured" : "not configured",
        connected_clients: connectedClients.size,
      })
    );
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
});

// ---------------------------------------------------------------------------
// WebSocket 服务（与 AI Parenting 后端通信）
// ---------------------------------------------------------------------------

let WebSocket;
let wss;
const connectedClients = new Set();

try {
  WebSocket = require("ws");
  const { WebSocketServer } = WebSocket;
  wss = new WebSocketServer({ port: WS_PORT });

  wss.on("connection", (ws, req) => {
    console.log(`[WS] Client connected from ${req.socket.remoteAddress}`);
    connectedClients.add(ws);

    ws.on("message", async (data) => {
      try {
        const msg = JSON.parse(data.toString());
        console.log(`[WS] Received: type=${msg.type}, channel=${msg.channel}`);

        // 处理来自后端的出站消息
        if (msg.type === "outbound") {
          await routeOutboundMessage(msg);
          ws.send(JSON.stringify({ type: "ack", id: msg.id, status: "sent" }));
        }
      } catch (err) {
        console.error("[WS] Message handling error:", err.message);
        ws.send(
          JSON.stringify({ type: "error", error: err.message })
        );
      }
    });

    ws.on("close", () => {
      connectedClients.delete(ws);
      console.log("[WS] Client disconnected");
    });

    // 发送欢迎消息
    ws.send(
      JSON.stringify({
        type: "connected",
        gateway: "openclaw",
        version: "1.0.0",
        channels: getEnabledChannels(),
      })
    );
  });

  console.log(`[WS] WebSocket server listening on port ${WS_PORT}`);
} catch (err) {
  console.warn("[WS] ws module not found, WebSocket disabled:", err.message);
}

// ---------------------------------------------------------------------------
// 消息路由
// ---------------------------------------------------------------------------

async function routeOutboundMessage(msg) {
  const { channel, recipient, content } = msg;

  if (channel === "whatsapp" && process.env.WHATSAPP_ENABLED === "true") {
    // TODO: 集成 Baileys 库发送 WhatsApp 消息
    console.log(
      `[WhatsApp] Sending to ${recipient}: ${content.text?.substring(0, 50)}...`
    );
  } else if (channel === "telegram" && process.env.TELEGRAM_ENABLED === "true") {
    // TODO: 集成 grammY 库发送 Telegram 消息
    console.log(
      `[Telegram] Sending to ${recipient}: ${content.text?.substring(0, 50)}...`
    );
  } else {
    console.warn(`[Router] Channel '${channel}' not enabled or unknown`);
  }
}

function getEnabledChannels() {
  const channels = [];
  if (process.env.WHATSAPP_ENABLED === "true") channels.push("whatsapp");
  if (process.env.TELEGRAM_ENABLED === "true") channels.push("telegram");
  return channels;
}

// ---------------------------------------------------------------------------
// Webhook 转发（入站消息 → 后端）
// ---------------------------------------------------------------------------

async function forwardToBackend(channel, sender, content) {
  if (!WEBHOOK_URL) {
    console.warn("[Webhook] No WEBHOOK_URL configured, skipping forward");
    return;
  }

  const payload = {
    type: "inbound",
    channel,
    sender,
    content: { text: content, type: "text" },
    timestamp: new Date().toISOString(),
  };

  // HMAC-SHA256 签名
  if (WEBHOOK_SECRET) {
    const signData = Object.entries(payload)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`)
      .join("&");
    payload.signature = crypto
      .createHmac("sha256", WEBHOOK_SECRET)
      .update(signData)
      .digest("hex");
  }

  try {
    const response = await fetch(WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    console.log(`[Webhook] Forwarded to backend: status=${data.status}`);
  } catch (err) {
    console.error("[Webhook] Forward failed:", err.message);
  }
}

// ---------------------------------------------------------------------------
// 启动
// ---------------------------------------------------------------------------

httpServer.listen(HTTP_PORT, () => {
  console.log(`[HTTP] Management server listening on port ${HTTP_PORT}`);
  console.log(`[Gateway] OpenClaw Gateway started`);
  console.log(`  - WebSocket: ws://0.0.0.0:${WS_PORT}`);
  console.log(`  - HTTP: http://0.0.0.0:${HTTP_PORT}`);
  console.log(`  - Channels: ${getEnabledChannels().join(", ") || "none"}`);
  console.log(`  - Webhook: ${WEBHOOK_URL || "not configured"}`);
});

// 优雅关闭
process.on("SIGTERM", () => {
  console.log("[Gateway] Received SIGTERM, shutting down...");
  if (wss) wss.close();
  httpServer.close();
  process.exit(0);
});

process.on("SIGINT", () => {
  console.log("[Gateway] Received SIGINT, shutting down...");
  if (wss) wss.close();
  httpServer.close();
  process.exit(0);
});
