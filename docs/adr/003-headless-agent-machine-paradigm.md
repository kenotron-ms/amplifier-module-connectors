# ADR-003: Headless Agent Machine Paradigm

**Status:** Accepted  
**Date:** 2025-01-06  
**Deciders:** Ken  
**Context:** Supporting dedicated hardware for "always-on" AI agents

## Context and Problem Statement

A new paradigm is emerging where developers deploy AI agents on dedicated, "always-on" hardware:
- **Hardware:** Low-wattage, high-compute machines (Mac Minis, Intel NUCs, mini PCs)
- **Deployment:** Headless (no monitor), always connected
- **Interface:** Chat platforms (Slack, Teams) with excellent mobile apps
- **Goal:** Issue commands to agents from anywhere via mobile device

**Key Insight:** Chat platforms are becoming the primary UI for agent control because they already have:
- ✅ Excellent mobile apps (iOS, Android)
- ✅ Push notifications
- ✅ Rich formatting (code blocks, buttons, etc.)
- ✅ Threading/conversation management
- ✅ File sharing
- ✅ Cross-device sync

This shifts the connector architecture requirements:
- Not just for development, but for production deployment
- Need to support 24/7 uptime
- Mobile-first interaction model
- Reliable reconnection on network issues

## Decision Drivers

- **Always-On:** Agents run 24/7 on dedicated hardware
- **Mobile Control:** Primary interface is mobile Teams/Slack app
- **Reliability:** Must handle network interruptions gracefully
- **Cost:** Reasonable for individual developers running personal agents
- **Simplicity:** Easy to deploy and maintain

## Architectural Implications

### 1. Azure Relay is Production-Ready

**Previously:** Viewed tunneling as "development only"  
**Now:** Azure Relay is the production architecture

- Persistent WebSocket connection
- Auto-reconnection on network issues
- No need for public IP or port forwarding
- Works behind home routers/firewalls

### 2. No Distinction Between Dev and Prod

**Previously:** Separate dev (tunnel) and prod (deployed) architectures  
**Now:** Same architecture for both

- Developer's laptop: Same Azure Relay setup
- Headless Mac Mini: Same Azure Relay setup
- Consistent experience and configuration

### 3. Mobile-First Design

**Interface Priorities:**
1. Mobile Teams/Slack app (primary)
2. Desktop Teams/Slack app (secondary)
3. Web interface (tertiary)

**Design Implications:**
- Messages must be mobile-friendly (concise, scannable)
- Rich formatting for complex responses
- Push notifications for important events
- Support for voice input (mobile dictation)

### 4. State Persistence

**Requirement:** Agent state must survive restarts

- Conversation history persistence
- Session state recovery
- File/artifact storage
- Configuration management

**Implementation:**
- Use persistent storage (not just in-memory)
- Document backup/restore procedures
- Consider cloud storage for artifacts

## Decision Outcome

**Accepted:** Design connectors to support headless agent machines as first-class use case

### Design Principles

1. **No Tunneling Required**
   - Azure Relay for Teams (ADR-001)
   - Socket Mode for Slack (existing)
   - No ngrok, no port forwarding

2. **Production-Ready by Default**
   - Auto-reconnection logic
   - Error recovery
   - Health monitoring
   - Logging for remote debugging

3. **Mobile-Optimized Responses**
   - Concise messages
   - Rich formatting (code blocks, lists)
   - Progress indicators for long operations
   - Error messages with actionable steps

4. **Easy Deployment**
   - One-command setup
   - Environment variable configuration
   - Systemd/launchd service files
   - Auto-restart on failure

### Consequences

**Positive:**
- ✅ Supports emerging use case (headless agents)
- ✅ Mobile-first design improves all experiences
- ✅ Production-ready architecture from day one
- ✅ No separate dev/prod deployment paths
- ✅ Aligns with "AI agent as appliance" trend

**Negative:**
- ❌ Higher bar for reliability (can't just restart manually)
- ❌ Need better error recovery and logging
- ❌ Documentation must cover 24/7 deployment scenarios

**Neutral:**
- 🔄 May need to add monitoring/alerting in future
- 🔄 Consider health check endpoints
- 🔄 Document power/network failure recovery

## Implementation Checklist

### Reliability Features
- [ ] Auto-reconnection for Azure Relay WebSocket
- [ ] Exponential backoff on connection failures
- [ ] Health check endpoint for monitoring
- [ ] Structured logging for remote debugging
- [ ] Graceful shutdown handling

### Deployment Support
- [ ] Systemd service file (Linux)
- [ ] Launchd plist (macOS)
- [ ] Docker Compose example
- [ ] Environment variable documentation
- [ ] Backup/restore procedures

### Mobile Optimization
- [ ] Concise message formatting
- [ ] Progress indicators for long operations
- [ ] Rich formatting (code blocks, buttons)
- [ ] Error messages with next steps
- [ ] Support for voice input (text normalization)

### Documentation
- [ ] Headless deployment guide
- [ ] Hardware recommendations (Mac Mini, NUC, etc.)
- [ ] Network configuration (router, firewall)
- [ ] Troubleshooting guide for remote debugging
- [ ] Cost analysis (hardware + Azure resources)

## Example Hardware Setups

### Budget Setup (~$500)
- **Device:** Intel NUC or Raspberry Pi 5
- **RAM:** 16GB
- **Storage:** 256GB SSD
- **Power:** 15-20W typical
- **Cost:** $400 hardware + ~$10/month Azure

### Performance Setup (~$1000)
- **Device:** Mac Mini M2
- **RAM:** 16GB
- **Storage:** 512GB SSD
- **Power:** 10-15W typical
- **Cost:** $800 hardware + ~$10/month Azure

### Enterprise Setup (~$2000)
- **Device:** Mac Mini M2 Pro
- **RAM:** 32GB
- **Storage:** 1TB SSD
- **Power:** 15-20W typical
- **Cost:** $1800 hardware + ~$10/month Azure

## Links

- [ADR-001: Azure Relay for Teams Local Development](./001-azure-relay-for-teams-local-development.md)
- [ADR-002: Per-Developer Bot Registration Model](./002-per-developer-bot-registration-model.md)
- [GitHub Issue: Implement Azure Relay for Teams](../.github/ISSUE_TEMPLATE/teams-azure-relay.md)
