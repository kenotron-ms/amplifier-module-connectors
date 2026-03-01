# GitHub Issue: Implement Azure Relay for Teams Connector

**Title:** Implement Azure Relay Hybrid Connections for Teams Connector

**Labels:** `enhancement`, `teams-connector`, `architecture`

---

## Problem Statement

The current Teams connector requires developers to use tunneling solutions (ngrok) for local development, which creates significant friction:

- **ngrok free tier**: Random URLs that change on every restart, requiring reconfiguration
- **Session timeouts**: Tunnels expire and need manual restart
- **Developer friction**: Extra setup step that's error-prone
- **Not production-ready**: Tunneling is a development-only workaround

**In contrast**, the Slack connector uses Socket Mode (persistent WebSocket), allowing developers to run locally without any tunneling.

## Proposed Solution

Implement **Azure Relay Hybrid Connections** as a proxy layer between Teams and local bot instances. This provides a "Socket Mode-like" experience for Teams.

### Architecture

```
Teams → Azure Bot Service → Azure Function → Azure Relay ←(WebSocket)← Local Bot
```

**Components:**
1. **Azure Relay Namespace** - Managed WebSocket relay service
2. **Azure Function** - Receives Teams webhooks, forwards to Relay
3. **Updated TeamsAdapter** - Connects to Relay instead of running webhook server
4. **Bicep Deployment Template** - One-click infrastructure provisioning

### Developer Experience

```bash
# One-time setup (per developer)
./deploy-teams-relay.sh

# Daily usage (no tunnel needed!)
export AZURE_RELAY_CONNECTION_STRING="..."
python -m teams_connector --bundle ./my-bundle.md
```

## Implementation Tasks

### Phase 1: Core Infrastructure
- [ ] Create Bicep template for Azure Relay + Function
- [ ] Implement Azure Function (webhook → Relay forwarder)
- [ ] Add deployment script with Azure CLI
- [ ] Document Azure resource costs (~$10/month)

### Phase 2: TeamsAdapter Refactor
- [ ] Replace deprecated `botbuilder-core` with `microsoft-agents-hosting-aiohttp`
- [ ] Implement Relay client in TeamsAdapter
- [ ] Remove webhook server code (no longer needed)
- [ ] Handle reconnection logic for Relay WebSocket

### Phase 3: Documentation & Testing
- [ ] Update Teams setup documentation
- [ ] Add integration tests with Relay
- [ ] Create troubleshooting guide
- [ ] Create migration guide from webhook-based approach

### Phase 4: Multi-Tenancy Considerations (Future)
- [ ] Document per-user vs shared relay tradeoffs
- [ ] Consider: Can multiple devs share one bot registration?
- [ ] Explore: Routing strategy for shared relay (if feasible)

## Open Questions

### Bot Registration Model
**Question:** Does each developer need their own bot registration, or can they share?

**Current Decision (ADR-002):** Per-developer bot registration
- ✅ Complete isolation
- ✅ No routing complexity
- ✅ Matches Slack pattern
- ❌ Each dev manages their own Azure resources (~$10/month)

### Relay Sharing Model
**Question:** Can multiple developers share one Azure Relay?

**Current Decision (ADR-002):** Per-developer relay initially
- Each dev deploys their own relay
- Complete isolation, simple
- Can revisit if cost becomes prohibitive

## Success Criteria

- [ ] Developers can run Teams connector locally without ngrok
- [ ] Setup takes < 5 minutes after Azure resources deployed
- [ ] Connection is stable (auto-reconnects on network issues)
- [ ] Documentation clearly explains architecture and costs
- [ ] Migration path from current webhook-based approach
- [ ] Support for 24/7 "always-on" headless agents

## Related Documentation

- [Implementation Plan](../teams-azure-relay-plan.md)
- [ADR-001: Azure Relay for Teams Local Development](../adr/001-azure-relay-for-teams-local-development.md)
- [ADR-002: Per-Developer Bot Registration Model](../adr/002-per-developer-bot-registration-model.md)
- [ADR-003: Headless Agent Machine Paradigm](../adr/003-headless-agent-machine-paradigm.md)

## Timeline

**Estimated:** 4-5 weeks

- Week 1-2: Phase 1 (Core Infrastructure)
- Week 3-4: Phase 2 (TeamsAdapter Refactor)
- Week 5: Phase 3 (Documentation & Testing)
- Future: Phase 4 (Multi-Tenancy considerations)

## References

- [Azure Relay Hybrid Connections](https://learn.microsoft.com/en-us/azure/azure-relay/relay-hybrid-connections-protocol)
- [Microsoft 365 Agents SDK](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/)
- [Bot Framework SDK Deprecation](https://github.com/microsoft/botbuilder-python)

---

**To create this issue on GitHub:**
```bash
gh issue create --title "Implement Azure Relay Hybrid Connections for Teams Connector" \
  --body-file docs/issues/teams-azure-relay-implementation.md \
  --label "enhancement,teams-connector,architecture"
```
