# ADR-001: Azure Relay Hybrid Connections for Teams Local Development

**Status:** Proposed  
**Date:** 2025-01-06  
**Deciders:** Ken  
**Context:** Teams connector architecture for local development

## Context and Problem Statement

The Teams connector requires a publicly accessible HTTPS endpoint to receive webhooks from Microsoft Teams. This creates friction for local development:

1. **Tunneling solutions (ngrok, etc.) are problematic:**
   - Free tier generates random URLs on every restart
   - Requires manual reconfiguration of Azure Bot Service messaging endpoint
   - Session timeouts require manual restarts
   - Not suitable for production or "always-on" scenarios

2. **Slack connector has superior DX:**
   - Uses Socket Mode (persistent WebSocket)
   - Bot connects *outbound* to Slack
   - No public endpoint needed
   - Works behind firewalls
   - Simple developer experience

3. **Teams doesn't offer Socket Mode equivalent:**
   - Only supports HTTP webhooks
   - Requires public HTTPS endpoint
   - No built-in persistent connection option

## Decision Drivers

- **Developer Experience:** Minimize setup friction, avoid manual URL reconfiguration
- **Consistency:** Match Slack connector's simple local development experience
- **Production Readiness:** Support "always-on" agents on dedicated hardware (headless Mac Minis, mini PCs)
- **Cost:** Keep Azure costs reasonable for individual developers
- **Security:** Avoid exposing local development machines directly to internet

## Considered Options

### Option 1: ngrok (Current Approach)
**Architecture:** `Teams → Azure Bot Service → ngrok tunnel → Local Bot`

**Pros:**
- ✅ Simple to understand
- ✅ No Azure resources needed
- ✅ Free tier available

**Cons:**
- ❌ Random URLs on free tier (requires reconfiguration)
- ❌ Session timeouts
- ❌ Manual restart required
- ❌ Not production-ready
- ❌ Paid tier needed for static URLs ($8/month)

**Verdict:** ❌ Rejected - Poor developer experience

---

### Option 2: Azure Relay Hybrid Connections (Recommended)
**Architecture:** `Teams → Azure Bot Service → Azure Function → Azure Relay ←(WebSocket)← Local Bot`

**Pros:**
- ✅ No tunneling needed
- ✅ Persistent WebSocket connection (like Slack Socket Mode)
- ✅ Bot connects *outbound* (works behind firewalls)
- ✅ Production-ready
- ✅ Auto-reconnection support
- ✅ Microsoft-managed infrastructure
- ✅ Supports "always-on" headless agents

**Cons:**
- ❌ Requires Azure resources (~$10/month per developer)
- ❌ More complex initial setup
- ❌ Need to build proxy layer (Azure Function)

**Verdict:** ✅ **Selected** - Best balance of DX and reliability

---

### Option 3: Azure Service Bus Queue (Polling)
**Architecture:** `Teams → Azure Function → Service Bus Queue ← Local Bot (polling)`

**Pros:**
- ✅ No inbound connections
- ✅ Simple to understand
- ✅ Built-in retry/reliability

**Cons:**
- ❌ Higher latency (polling-based)
- ❌ Not real-time
- ❌ Still requires Azure Function
- ❌ More expensive than Relay for this use case

**Verdict:** ❌ Rejected - Polling latency unacceptable

---

### Option 4: Direct Line App Service Extension
**Architecture:** `Teams → Direct Line Channel (WebSocket) ←─ Local Bot`

**Pros:**
- ✅ Official Microsoft solution
- ✅ WebSocket-based

**Cons:**
- ❌ Only works with Direct Line channel (not Teams channel directly)
- ❌ More complex setup
- ❌ Requires bot in Azure App Service (defeats local development goal)
- ❌ Documentation unclear on local development support

**Verdict:** ❌ Rejected - Doesn't support local development properly

## Decision Outcome

**Chosen Option:** Azure Relay Hybrid Connections

We will implement an Azure Relay-based proxy architecture that provides a Socket Mode-like experience for Teams developers.

### Implementation Components

1. **Azure Relay Namespace**
   - Managed WebSocket relay service
   - Provides persistent bidirectional connection
   - Cost: ~$10/month (Standard tier, 1000 listener hours)

2. **Azure Function (Webhook Proxy)**
   - Receives Teams webhooks at `/api/messages`
   - Forwards activities to Azure Relay
   - Minimal code, stateless
   - Cost: Free tier (1M executions/month)

3. **Updated TeamsAdapter**
   - Connects to Azure Relay via WebSocket
   - No webhook server needed
   - Handles reconnection logic
   - Uses `azure-relay` Python SDK

4. **Bicep Deployment Template**
   - One-click infrastructure provisioning
   - Outputs connection string for local bot
   - Consistent naming conventions

### Developer Workflow

```bash
# One-time setup (per developer)
./deploy-teams-relay.sh
# Outputs: AZURE_RELAY_CONNECTION_STRING

# Daily usage (no tunnel!)
export AZURE_RELAY_CONNECTION_STRING="Endpoint=sb://..."
python -m teams_connector --bundle ./my-bundle.md
```

### Consequences

**Positive:**
- ✅ Matches Slack connector's simple DX
- ✅ No more ngrok URL reconfiguration
- ✅ Production-ready for headless agent machines
- ✅ Works behind corporate firewalls
- ✅ Auto-reconnection on network issues
- ✅ Supports mobile control via Teams mobile app

**Negative:**
- ❌ Each developer pays ~$10/month for Azure resources
- ❌ Requires Azure subscription
- ❌ More complex architecture (but abstracted from users)
- ❌ Migration effort from current webhook-based approach

**Neutral:**
- 🔄 Need to migrate from deprecated `botbuilder-core` to `microsoft-agents-hosting-aiohttp` anyway
- 🔄 Per-developer bot registration model (same as Slack)

## Links

- [Azure Relay Hybrid Connections Documentation](https://learn.microsoft.com/en-us/azure/azure-relay/relay-hybrid-connections-protocol)
- [Azure Relay Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/relay)
- [GitHub Issue: Implement Azure Relay for Teams](../.github/ISSUE_TEMPLATE/teams-azure-relay.md)
