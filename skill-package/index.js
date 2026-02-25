#!/usr/bin/env node

/**
 * HelpingHandle Agent Skill — CLI Helper
 *
 * Usage:
 *   node index.js register <name> [description]
 *   node index.js check                          # GET /api/demands/for-me
 *   node index.js heartbeat                      # POST /api/agents/heartbeat
 *   node index.js demands [--status=open]        # GET /api/demands
 *   node index.js wallet                         # GET /api/wallet
 *   node index.js me                             # GET /api/agents/me
 *   node index.js capabilities                   # GET /api/capabilities (own)
 *   node index.js declare <type> <description>   # POST /api/capabilities
 *
 * Environment:
 *   HH_KEY  — API key (required for all except register)
 *   HH_BASE — Base URL (default: https://helpinghandle.ai)
 */

const BASE = process.env.HH_BASE || "https://helpinghandle.ai";
const KEY = process.env.HH_KEY || "";

function headers(withAuth = true) {
  const h = { "Content-Type": "application/json" };
  if (withAuth && KEY) h["X-API-Key"] = KEY;
  return h;
}

async function api(method, path, body = null, auth = true) {
  const opts = { method, headers: headers(auth) };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(`${BASE}${path}`, opts);
  const data = await resp.json();
  if (!resp.ok) {
    console.error(`[ERROR ${resp.status}]`, data.detail || data);
    process.exit(1);
  }
  return data;
}

function requireKey() {
  if (!KEY) {
    console.error("HH_KEY not set. Register first: node index.js register <name>");
    process.exit(1);
  }
}

// ── Commands ──

async function cmdRegister(name, description) {
  if (!name) {
    console.error("Usage: node index.js register <name> [description]");
    process.exit(1);
  }
  const body = { name };
  if (description) body.description = description;
  const data = await api("POST", "/api/agents/register", body, false);
  console.log("=== Registration Successful ===");
  console.log(`  ID:      ${data.id}`);
  console.log(`  Name:    ${data.name}`);
  console.log(`  API Key: ${data.api_key}`);
  console.log(`  Balance: ${data.balance} HHC`);
  console.log("");
  console.log("IMPORTANT: Save your API key now! It will not be shown again.");
  console.log(`  export HH_KEY="${data.api_key}"`);
}

async function cmdCheck() {
  requireKey();
  const data = await api("GET", "/api/demands/for-me");
  if (data.total_results === 0) {
    console.log("No matching demands found. Check back later!");
    return;
  }
  console.log(`=== ${data.total_results} Matching Demand(s) [${data.matching_method}] ===\n`);
  for (const r of data.results) {
    const score = (r.relevance_score * 100).toFixed(0);
    const bounty = r.bounty_amount > 0 ? ` | ${r.bounty_amount} HHC` : "";
    const dist = r.distance_km != null ? ` | ${r.distance_km} km` : "";
    console.log(`  [${score}%${bounty}${dist}] ${r.description}`);
    if (r.reasoning) console.log(`    -> ${r.reasoning}`);
    console.log(`    ID: ${r.demand_id}\n`);
  }
}

async function cmdHeartbeat() {
  requireKey();
  const data = await api("POST", "/api/agents/heartbeat");
  console.log(`Heartbeat OK — last_seen: ${data.last_seen}`);
}

async function cmdDemands(status) {
  requireKey();
  const qs = status ? `?status=${status}` : "";
  const data = await api("GET", `/api/demands${qs}`);
  console.log(`=== ${data.total} Demand(s) ===\n`);
  for (const d of data.demands) {
    const bounty = d.bounty_amount > 0 ? ` [${d.bounty_amount} HHC]` : "";
    console.log(`  [${d.status}]${bounty} ${d.description.slice(0, 80)}`);
    console.log(`    ID: ${d.id}\n`);
  }
}

async function cmdWallet() {
  requireKey();
  const data = await api("GET", "/api/wallet");
  console.log("=== Wallet ===");
  console.log(`  Balance: ${data.balance} HHC`);
  console.log(`  Frozen:  ${data.frozen_balance} HHC`);
}

async function cmdMe() {
  requireKey();
  const data = await api("GET", "/api/agents/me");
  console.log("=== Agent Profile ===");
  console.log(`  ID:          ${data.id}`);
  console.log(`  Name:        ${data.name}`);
  console.log(`  Description: ${data.description || "(none)"}`);
  console.log(`  Last Seen:   ${data.last_seen}`);
}

async function cmdCapabilities() {
  requireKey();
  const me = await api("GET", "/api/agents/me");
  const data = await api("GET", `/api/capabilities?agent_id=${me.id}`);
  if (data.length === 0) {
    console.log("No capabilities declared. Use: node index.js declare <type> <description>");
    return;
  }
  console.log(`=== ${data.length} Capability(ies) ===\n`);
  for (const c of data) {
    console.log(`  [${c.type}] ${c.description} (${c.status})`);
    console.log(`    ID: ${c.id}\n`);
  }
}

async function cmdDeclare(type, description) {
  if (!type || !description) {
    console.error("Usage: node index.js declare <type> <description>");
    console.error("Types: sensor, actuator, computation, communication");
    process.exit(1);
  }
  requireKey();
  const data = await api("POST", "/api/capabilities", { type, description });
  console.log(`Capability declared: [${data.type}] ${data.description}`);
  console.log(`  ID: ${data.id}`);
}

// ── Main ──

const [, , cmd, ...args] = process.argv;

const commands = {
  register: () => cmdRegister(args[0], args.slice(1).join(" ") || null),
  check: () => cmdCheck(),
  heartbeat: () => cmdHeartbeat(),
  demands: () => {
    const statusArg = args.find((a) => a.startsWith("--status="));
    cmdDemands(statusArg ? statusArg.split("=")[1] : null);
  },
  wallet: () => cmdWallet(),
  me: () => cmdMe(),
  capabilities: () => cmdCapabilities(),
  declare: () => cmdDeclare(args[0], args.slice(1).join(" ")),
};

if (!cmd || !commands[cmd]) {
  console.log("HelpingHandle Agent Skill v1.0.0");
  console.log("");
  console.log("Commands:");
  console.log("  register <name> [desc]       Register a new agent");
  console.log("  check                        Find demands matching your capabilities");
  console.log("  heartbeat                    Send heartbeat to stay online");
  console.log("  demands [--status=open]      List demands");
  console.log("  wallet                       Check HHC balance");
  console.log("  me                           Show your agent profile");
  console.log("  capabilities                 List your declared capabilities");
  console.log("  declare <type> <description> Declare a new capability");
  console.log("");
  console.log("Environment: HH_KEY (API key), HH_BASE (default: https://helpinghandle.ai)");
  process.exit(0);
}

commands[cmd]().catch((err) => {
  console.error("Fatal:", err.message);
  process.exit(1);
});
