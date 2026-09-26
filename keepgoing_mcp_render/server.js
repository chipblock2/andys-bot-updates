import express from "express";
import crypto from "crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const app = express();
const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET || "";
const PRO_PRICE_ID = process.env.KEEPGOING_PRO_PRICE_ID || "price_1UJy24B86Ss16l9WEsqSRxh1";
const BUSINESS_PRICE_ID = process.env.KEEPGOING_BUSINESS_PRICE_ID || "price_1UJy26B86Ss16l9W8id4FSsw";

app.post("/stripe/webhook", express.raw({ type: "application/json" }), async (req, res) => {
  if (!STRIPE_WEBHOOK_SECRET) return res.status(503).send("Stripe webhook not configured");
  const header = String(req.headers["stripe-signature"] || "");
  const parts = Object.fromEntries(header.split(",").map((p) => p.split("=", 2)));
  const timestamp = parts.t || "";
  const signature = parts.v1 || "";
  if (!timestamp || !signature) return res.status(400).send("Invalid webhook signature");

  const age = Math.abs(Math.floor(Date.now() / 1000) - Number(timestamp));
  if (!Number.isFinite(age) || age > 300) return res.status(400).send("Webhook timestamp outside tolerance");

  const payload = req.body.toString("utf8");
  const expected = crypto
    .createHmac("sha256", STRIPE_WEBHOOK_SECRET)
    .update(timestamp + "." + payload, "utf8")
    .digest("hex");

  let verified = false;
  try {
    verified = crypto.timingSafeEqual(Buffer.from(expected, "hex"), Buffer.from(signature, "hex"));
  } catch {}
  if (!verified) return res.status(400).send("Invalid webhook signature");

  let event;
  try { event = JSON.parse(payload); }
  catch { return res.status(400).send("Invalid JSON"); }

  const relevant = new Set([
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed"
  ]);

  if (relevant.has(event.type)) {
    console.log("stripe_event", event.type, event.data?.object?.id || "");
  }
  return res.json({ received: true });
});

app.use(express.json({ limit: "256kb" }));

const PORT = Number(process.env.PORT || 10000);
const MODEL = process.env.OPENAI_MODEL || "gpt-5.2";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";
const TOKEN_HASH = "300caf15b670e9aa648ffc6aa9f7249297566ff6b0ba37898ee4f2da7bd91697";

function digest(value) {
  return crypto.createHash("sha256").update(value || "").digest("hex");
}

function authorised(req) {
  const queryToken = typeof req.query?.token === "string" ? req.query.token : "";
  const headerToken = req.get("x-keepgoing-token") || "";
  const auth = req.get("authorization") || "";
  const bearer = auth.toLowerCase().startsWith("bearer ") ? auth.slice(7).trim() : "";
  return [queryToken, headerToken, bearer].some((v) => v && digest(v) === TOKEN_HASH);
}

function outputText(data) {
  if (typeof data?.output_text === "string") return data.output_text;
  const parts = [];
  for (const item of data?.output || []) {
    for (const c of item?.content || []) {
      if (c?.type === "output_text" && typeof c.text === "string") parts.push(c.text);
    }
  }
  return parts.join("\n");
}

async function openai(path, init = {}) {
  if (!OPENAI_API_KEY) throw new Error("KeepGoing OpenAI key is not configured");
  const response = await fetch("https://api.openai.com/v1" + path, {
    ...init,
    headers: {
      Authorization: "Bearer " + OPENAI_API_KEY,
      "Content-Type": "application/json",
      ...(init.headers || {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.error?.message || ("OpenAI request failed (" + response.status + ")"));
  return data;
}

function jobPrompt(goal, done, mode) {
  const autonomy = {
    safe: "Be cautious. Do not make assumptions where missing information changes the result.",
    balanced: "Work autonomously where reasonable, verify important points, and minimise unnecessary questions.",
    max: "Work as autonomously and comprehensively as possible within the available tools and information."
  }[mode] || "Work autonomously where reasonable.";

  return [
    "You are the execution engine for KeepGoing, a persistent background AI job runner.",
    "",
    "GOAL:", goal,
    "",
    "DEFINITION OF DONE:", done,
    "",
    "AUTONOMY:", autonomy,
    "",
    "Complete the job as fully as possible in this background run.",
    "Do not stop merely because a normal chat response would have ended or because you would usually ask whether to continue.",
    "Never claim to have performed actions outside the tools actually available to this response.",
    "If an essential credential, approval, payment, destructive action, private account action, or missing fact prevents completion, return NEEDS_USER and state exactly what is required.",
    "",
    "End with one of:",
    "STATUS: COMPLETED",
    "STATUS: NEEDS_USER",
    "STATUS: PARTIAL",
    "",
    "Then include a concise WORK_COMPLETED section and RESULT."
  ].join("\n");
}

async function startJob({ goal, definitionOfDone, mode, allowWeb }) {
  const body = {
    model: MODEL,
    input: jobPrompt(goal, definitionOfDone, mode),
    background: true,
    store: true
  };
  if (allowWeb) body.tools = [{ type: "web_search" }];
  const data = await openai("/responses", { method: "POST", body: JSON.stringify(body) });
  return {
    job_id: data.id,
    status: data.status,
    model: data.model || MODEL,
    message: "KeepGoing job started. Reuse this job_id with get_persistent_job instead of starting a duplicate."
  };
}

async function getJob(jobId) {
  const data = await openai("/responses/" + encodeURIComponent(jobId), { method: "GET" });
  return {
    job_id: data.id,
    status: data.status,
    output: outputText(data),
    error: data.error?.message || null,
    incomplete_details: data.incomplete_details || null
  };
}

async function cancelJob(jobId) {
  const data = await openai("/responses/" + encodeURIComponent(jobId) + "/cancel", {
    method: "POST",
    body: "{}"
  });
  return { job_id: data.id || jobId, status: data.status || "cancelled" };
}

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled", "expired", "incomplete"]);

async function waitForJob(jobId, waitSeconds = 20) {
  const deadline = Date.now() + Math.max(1, Math.min(Number(waitSeconds) || 20, 25)) * 1000;
  let latest = await getJob(jobId);
  while (!TERMINAL_STATUSES.has(latest.status) && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    latest = await getJob(jobId);
  }
  return {
    ...latest,
    should_continue_polling: !TERMINAL_STATUSES.has(latest.status),
    message: TERMINAL_STATUSES.has(latest.status)
      ? "KeepGoing reached a terminal state."
      : "KeepGoing is still running. Call wait_for_persistent_job again with the same job_id. Do not ask the user to type continue."
  };
}

function createMcpServer() {
  const server = new McpServer(
    { name: "KeepGoing", version: "0.6.0" },
    { instructions: "Use KeepGoing for substantial model-only work or research that should continue as a background response instead of stopping at a normal chat-turn boundary. Start one job, preserve its job_id, then call wait_for_persistent_job. If should_continue_polling is true, call wait_for_persistent_job again with the same job_id without asking the user to type continue. Reuse the same job_id and never create duplicate jobs just to keep working. KeepGoing does not automatically control other ChatGPT plugins, desktops, payments, or private accounts." }
  );

  server.registerTool("start_persistent_job", {
    description: "Start a persistent OpenAI background job so substantial model work or research can continue without repeated continue prompts.",
    inputSchema: {
      goal: z.string().min(1).max(12000),
      definitionOfDone: z.string().min(1).max(4000).default("All requested work completed and verified"),
      mode: z.enum(["safe","balanced","max"]).default("balanced"),
      allowWeb: z.boolean().default(true)
    }
  }, async (args) => {
    try {
      const result = await startJob(args);
      return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: String(error?.message || error) }] };
    }
  });

  server.registerTool("get_persistent_job", {
    description: "Check the current state and output of an existing KeepGoing job. Keep polling the same job_id until it completes or needs the user.",
    inputSchema: { job_id: z.string().min(1).max(200) }
  }, async ({ job_id }) => {
    try {
      const result = await getJob(job_id);
      return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: String(error?.message || error) }] };
    }
  });

  server.registerTool("wait_for_persistent_job", {
    description: "Wait and poll an existing KeepGoing job for up to 25 seconds. If should_continue_polling is true, call this tool again with the same job_id automatically instead of asking the user to type continue.",
    inputSchema: {
      job_id: z.string().min(1).max(200),
      wait_seconds: z.number().int().min(1).max(25).default(20)
    }
  }, async ({ job_id, wait_seconds }) => {
    try {
      const result = await waitForJob(job_id, wait_seconds);
      return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: String(error?.message || error) }] };
    }
  });

  server.registerTool("cancel_persistent_job", {
    description: "Cancel a KeepGoing background job.",
    inputSchema: { job_id: z.string().min(1).max(200) }
  }, async ({ job_id }) => {
    try {
      const result = await cancelJob(job_id);
      return { content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result };
    } catch (error) {
      return { isError: true, content: [{ type: "text", text: String(error?.message || error) }] };
    }
  });

  return server;
}

app.get("/billing/success", (req, res) => {
  res.type("html").send(`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>KeepGoing subscription</title><style>body{font-family:system-ui;background:#0d1117;color:#fff;display:grid;place-items:center;min-height:100vh;margin:0}.card{max-width:560px;padding:32px;background:#161b22;border:1px solid #30363d;border-radius:18px}a{color:#58a6ff}</style></head><body><div class="card"><h1>KeepGoing subscription received</h1><p>Your Stripe checkout completed in this environment. Keep this page open while KeepGoing confirms your subscription.</p><p><a href="/">Return to KeepGoing</a></p></div></body></html>`);
});

app.get("/billing/plans", (_req, res) => {
  res.json({
    free: { price_gbp: 0, jobs_per_month: 3 },
    pro: { price_gbp: 7.99, price_id: PRO_PRICE_ID, jobs_per_month: 100, checkout_url: "https://buy.stripe.com/test_aFa14m1Jeaee3Wg3WEao800" },
    business: { price_gbp: 29, price_id: BUSINESS_PRICE_ID, jobs_per_month: 500, checkout_url: "https://buy.stripe.com/test_fZu6oG73yfyygJ28cUao801" }
  });
});

app.get("/health", (_req, res) => {
  res.json({ ok: true, name: "KeepGoing MCP", version: "0.6.0", openaiConfigured: Boolean(OPENAI_API_KEY), protected: true, model: MODEL });
});

app.post("/mcp", async (req, res) => {
  if (!authorised(req)) return res.status(401).json({ error: "unauthorized" });
  const server = createMcpServer();
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  res.on("close", async () => {
    try { await transport.close(); } catch {}
    try { await server.close(); } catch {}
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch {
    if (!res.headersSent) res.status(500).json({ error: "mcp_error" });
  }
});

app.get("/mcp", (req, res) => {
  if (!authorised(req)) return res.status(401).json({ error: "unauthorized" });
  res.status(405).json({ error: "Use POST for stateless MCP" });
});

app.listen(PORT, "0.0.0.0", () => console.log("KeepGoing MCP v0.6.0 listening on " + PORT));
