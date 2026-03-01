# Teams Azure Relay Architecture Plan

**Status:** Planning Phase  
**Last Updated:** 2025-01-06

## Executive Summary

This document outlines the plan to migrate the Teams connector from a tunnel-based (ngrok) architecture to an Azure Relay-based architecture that provides a "Socket Mode-like" experience similar to the Slack connector.

## Problem Statement

The current Teams connector requires developers to use tunneling solutions (ngrok) for local development, which creates significant friction:

- **Random URLs** on ngrok free tier require manual reconfiguration
- **Session timeouts** require manual restarts
- **Not production-ready** for "always-on" headless agent machines
- **Inconsistent** with Slack connector's simple Socket Mode experience

## Proposed Solution

Implement **Azure Relay Hybrid Connections** as a proxy layer between Teams and local bot instances.

### Architecture

```
Teams → Azure Bot Service → Azure Function → Azure Relay ←(WebSocket)← Local Bot
```

### Key Benefits

- ✅ No tunneling required
- ✅ Persistent WebSocket connection (like Slack Socket Mode)
- ✅ Works behind firewalls
- ✅ Production-ready for headless agents
- ✅ Auto-reconnection on network issues

## Documentation

### Architecture Decision Records

Three ADRs document the architectural choices and rationale:

1. **[ADR-001: Azure Relay for Teams Local Development](./adr/001-azure-relay-for-teams-local-development.md)**
   - Compares tunneling vs Azure Relay vs Service Bus vs Direct Line
   - Documents why Azure Relay was chosen
   - Outlines implementation components

2. **[ADR-002: Per-Developer Bot Registration Model](./adr/002-per-developer-bot-registration-model.md)**
   - Compares per-developer vs shared bot registration
   - Documents why per-developer model was chosen
   - Matches Slack connector pattern

3. **[ADR-003: Headless Agent Machine Paradigm](./adr/003-headless-agent-machine-paradigm.md)**
   - Documents emerging paradigm of dedicated agent hardware
   - Design implications for mobile-first control
   - Production-ready architecture requirements

### GitHub Issue

**[Issue: Implement Azure Relay for Teams Connector](.github/ISSUE_TEMPLATE/teams-azure-relay.md)**

Tracks implementation tasks:
- Phase 1: Core Infrastructure (Bicep, Function, deployment)
- Phase 2: TeamsAdapter Refactor (migrate to new SDK)
- Phase 3: Documentation & Testing
- Phase 4: Multi-Tenancy Considerations

## Key Architectural Decisions

### 1. Azure Relay Over Tunneling

**Rationale:**
- Persistent WebSocket connection (no URL reconfiguration)
- Production-ready (supports 24/7 uptime)
- Works behind firewalls (bot connects outbound)
- Microsoft-managed infrastructure

**Trade-off:**
- Cost: ~$10/month per developer
- Complexity: Requires Azure resources

**Verdict:** Developer experience and production readiness outweigh cost concerns

### 2. Per-Developer Bot Registration

**Rationale:**
- Complete isolation between developers
- No routing complexity
- Matches Slack connector pattern
- Simple to debug and maintain

**Trade-off:**
- Each developer pays ~$10/month
- Multiple bot registrations to manage

**Verdict:** Simplicity and isolation outweigh cost concerns

### 3. Support Headless Agent Machines

**Context:** Emerging paradigm where developers deploy agents on dedicated hardware (Mac Minis, mini PCs) that run 24/7, controlled via mobile chat apps.

**Implications:**
- Architecture must support production deployment, not just development
- Mobile-first design for control interface
- Reliable reconnection and error recovery
- State persistence and backup

## Implementation Plan

### Phase 1: Core Infrastructure

**Deliverables:**
- Bicep template for Azure Relay + Function
- Deployment script (`deploy-teams-relay.sh`)
- Azure Function (webhook → Relay forwarder)
- Documentation of Azure costs

**Estimated Effort:** 2-3 days

### Phase 2: TeamsAdapter Refactor

**Deliverables:**
- Migrate from deprecated `botbuilder-core` to `microsoft-agents-hosting-aiohttp`
- Implement Relay client in TeamsAdapter
- Remove webhook server code
- Add reconnection logic

**Estimated Effort:** 3-4 days

### Phase 3: Documentation & Testing

**Deliverables:**
- Updated Teams setup documentation
- Integration tests with Relay
- Troubleshooting guide
- Migration guide from webhook-based approach

**Estimated Effort:** 2-3 days

### Phase 4: Multi-Tenancy (Future)

**Open Questions:**
- Can multiple devs share one bot registration? (Likely no)
- Routing strategy for shared relay? (Likely not needed)
- Cost optimization strategies?

**Status:** Deferred until Phase 1-3 complete

## Cost Analysis

### Per-Developer Costs

**Azure Resources:**
- Azure Relay (Standard): ~$10/month
- Azure Function (Consumption): Free tier (1M executions/month)
- Azure Bot Service registration: Free

**Total:** ~$10/month per developer

### Headless Agent Machine Costs

**Hardware (one-time):**
- Budget: Intel NUC / Raspberry Pi 5 (~$400)
- Performance: Mac Mini M2 (~$800)
- Enterprise: Mac Mini M2 Pro (~$1800)

**Ongoing:**
- Azure resources: ~$10/month
- Electricity: ~$2-5/month (15W @ $0.12/kWh)

**Total:** $12-15/month ongoing after hardware purchase

## Open Questions

### Bot Registration Sharing

**Question:** Can developers share a single bot registration, or does each need their own?

**Current Thinking:** Per-developer model (matches Slack pattern)

**To Investigate:**
- Technical feasibility of shared registration with routing
- Conversation state isolation challenges
- Security implications

**Decision:** Start with per-developer, revisit if cost becomes prohibitive

### Relay Sharing

**Question:** Can multiple developers share one Azure Relay?

**Current Thinking:** Per-developer relay for simplicity

**To Investigate:**
- Azure Relay's multi-listener support
- Message routing strategies
- Cost savings vs complexity

**Decision:** Start with per-developer, revisit if needed

## Success Criteria

- [ ] Developers can run Teams connector locally without ngrok
- [ ] Setup takes < 5 minutes after Azure resources deployed
- [ ] Connection is stable (auto-reconnects on network issues)
- [ ] Documentation clearly explains architecture and costs
- [ ] Migration path from current webhook-based approach
- [ ] Support for 24/7 "always-on" headless agents

## Timeline

**Week 1-2:** Phase 1 (Core Infrastructure)  
**Week 3-4:** Phase 2 (TeamsAdapter Refactor)  
**Week 5:** Phase 3 (Documentation & Testing)  
**Future:** Phase 4 (Multi-Tenancy considerations)

## References

### Documentation
- [Architecture Decision Records](./adr/README.md)
- [GitHub Issue: Teams Azure Relay](.github/ISSUE_TEMPLATE/teams-azure-relay.md)

### Microsoft Documentation
- [Azure Relay Hybrid Connections](https://learn.microsoft.com/en-us/azure/azure-relay/relay-hybrid-connections-protocol)
- [Microsoft 365 Agents SDK](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/)
- [Bot Framework SDK Deprecation](https://github.com/microsoft/botbuilder-python)

### Related ADRs
- [ADR-001: Azure Relay for Teams Local Development](./adr/001-azure-relay-for-teams-local-development.md)
- [ADR-002: Per-Developer Bot Registration Model](./adr/002-per-developer-bot-registration-model.md)
- [ADR-003: Headless Agent Machine Paradigm](./adr/003-headless-agent-machine-paradigm.md)
