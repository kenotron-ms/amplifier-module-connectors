# ADR-002: Per-Developer Bot Registration Model

**Status:** Proposed  
**Date:** 2025-01-06  
**Deciders:** Ken  
**Context:** Bot registration and multi-tenancy for Teams connector

## Context and Problem Statement

When multiple developers use the Teams connector, we need to decide:
1. Does each developer provision their own bot registration in Azure?
2. Can developers share a single bot registration?
3. What are the implications for conversation routing and state management?

This decision impacts:
- Developer onboarding complexity
- Azure resource costs
- Conversation isolation
- Routing complexity

## Decision Drivers

- **Developer Isolation:** Each developer should have independent testing environments
- **Simplicity:** Minimize routing and state management complexity
- **Cost:** Balance Azure costs against architectural complexity
- **Consistency:** Match patterns from Slack connector where possible
- **Headless Agents:** Support dedicated "always-on" agent machines

## Considered Options

### Option 1: Per-Developer Bot Registration (Recommended)

**Architecture:**
```
Developer A: Teams → Bot A → Relay A → Dev A's Machine
Developer B: Teams → Bot B → Relay B → Dev B's Machine
```

Each developer provisions:
- Azure Bot Service registration
- Azure Relay namespace
- Azure Function (webhook proxy)

**Pros:**
- ✅ Complete isolation between developers
- ✅ No routing complexity
- ✅ No conversation state collision
- ✅ Matches Slack connector pattern (each dev has own Slack app)
- ✅ Simple to reason about
- ✅ Each dev controls their own resources
- ✅ Easy to debug (no shared infrastructure)

**Cons:**
- ❌ Each developer pays ~$10/month for Azure Relay
- ❌ Each developer needs Azure subscription
- ❌ More initial setup per developer

**Cost:** ~$10/month per developer (Azure Relay Standard tier)

**Verdict:** ✅ **Selected** - Simplicity and isolation outweigh cost concerns

---

### Option 2: Shared Bot Registration with Message Routing

**Architecture:**
```
Teams → Shared Bot → Shared Relay → Router → Multiple Local Bots
                                          ├→ Dev A's Machine
                                          ├→ Dev B's Machine
                                          └→ Dev C's Machine
```

**Routing Strategies:**
1. **User-based routing:** Route by Teams user ID
2. **Conversation-based routing:** Route by conversation ID
3. **Round-robin:** Distribute messages across connected bots

**Pros:**
- ✅ Single bot registration
- ✅ Shared Azure costs (~$10/month total)
- ✅ One bot for whole team

**Cons:**
- ❌ Complex routing logic required
- ❌ How to assign conversations to developers?
- ❌ Conversation state collision risks
- ❌ Debugging nightmare (which dev is handling this message?)
- ❌ Race conditions on message handling
- ❌ Doesn't match Slack pattern
- ❌ Not suitable for production "always-on" agents

**Verdict:** ❌ Rejected - Complexity outweighs cost savings

---

### Option 3: Hybrid (Shared Development Bot + Per-Agent Production Bots)

**Architecture:**
```
Development: Teams → Shared Bot → Shared Relay → Any Dev's Machine
Production:  Teams → Agent Bot → Dedicated Relay → Dedicated Agent Machine
```

**Pros:**
- ✅ Cost savings during development
- ✅ Production agents get dedicated resources

**Cons:**
- ❌ Two different architectures to maintain
- ❌ Still need routing logic for shared dev bot
- ❌ Confusing mental model

**Verdict:** ❌ Rejected - Adds complexity without clear benefit

## Decision Outcome

**Chosen Option:** Per-Developer Bot Registration (Option 1)

Each developer provisions their own:
1. Azure Bot Service registration (free)
2. Azure Relay namespace (~$10/month)
3. Azure Function (free tier)

### Rationale

1. **Matches Slack Pattern:**
   - Slack connector already requires per-developer Slack apps
   - Developers are familiar with this model
   - Consistent mental model across platforms

2. **Simplicity Over Cost:**
   - ~$10/month is acceptable for professional developers
   - Eliminates entire class of routing/state bugs
   - Faster to implement and maintain

3. **Supports Headless Agents:**
   - Each "always-on" agent machine gets dedicated resources
   - No shared infrastructure to manage
   - Clear ownership and billing

4. **Developer Experience:**
   - One-click deployment script
   - No coordination needed between developers
   - Easy to tear down and recreate

### Implementation Details

**Deployment Script:** `deploy-teams-relay.sh`
```bash
#!/bin/bash
# Provisions all Azure resources for one developer

# Creates:
# - Resource group: amplifier-teams-{username}
# - Azure Relay: amplifier-relay-{username}
# - Azure Function: amplifier-webhook-{username}
# - Bot registration: amplifier-bot-{username}

# Outputs:
# - AZURE_RELAY_CONNECTION_STRING
# - BOT_APP_ID
# - BOT_APP_PASSWORD
```

**Resource Naming:**
- Resource Group: `amplifier-teams-{username}`
- Relay Namespace: `amplifier-relay-{username}`
- Function App: `amplifier-webhook-{username}`
- Bot Registration: `amplifier-bot-{username}`

### Consequences

**Positive:**
- ✅ Simple architecture (no routing logic)
- ✅ Complete developer isolation
- ✅ Matches Slack connector pattern
- ✅ Production-ready for headless agents
- ✅ Easy to debug and troubleshoot

**Negative:**
- ❌ ~$10/month per developer for Azure Relay
- ❌ Each developer needs Azure subscription
- ❌ Multiple bot registrations to manage

**Neutral:**
- 🔄 Can revisit if cost becomes prohibitive
- 🔄 Could add shared development bot later if needed

### Future Considerations

**If cost becomes an issue:**
1. Provide option for shared development bot
2. Document tradeoffs clearly
3. Keep per-developer as default/recommended

**For enterprise deployments:**
1. Consider Azure Relay Premium tier (VNet integration)
2. Document cost optimization strategies
3. Consider managed identity for authentication

## Links

- [ADR-001: Azure Relay for Teams Local Development](./001-azure-relay-for-teams-local-development.md)
- [Azure Relay Pricing](https://azure.microsoft.com/en-us/pricing/details/service-bus/)
- [GitHub Issue: Implement Azure Relay for Teams](../.github/ISSUE_TEMPLATE/teams-azure-relay.md)
