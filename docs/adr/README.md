# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the Amplifier Connectors project.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences.

## ADR Index

### Active ADRs

- [ADR-001: Azure Relay for Teams Local Development](./001-azure-relay-for-teams-local-development.md)  
  **Status:** Proposed  
  **Summary:** Use Azure Relay Hybrid Connections instead of ngrok for Teams connector local development

- [ADR-002: Per-Developer Bot Registration Model](./002-per-developer-bot-registration-model.md)  
  **Status:** Proposed  
  **Summary:** Each developer provisions their own bot registration and Azure resources for isolation and simplicity

- [ADR-003: Headless Agent Machine Paradigm](./003-headless-agent-machine-paradigm.md)  
  **Status:** Accepted  
  **Summary:** Design connectors to support dedicated "always-on" hardware as first-class use case

## ADR Template

When creating a new ADR, use this template:

```markdown
# ADR-XXX: [Title]

**Status:** [Proposed | Accepted | Deprecated | Superseded]  
**Date:** YYYY-MM-DD  
**Deciders:** [Names]  
**Context:** [Brief context]

## Context and Problem Statement

[Describe the context and problem statement]

## Decision Drivers

- [Driver 1]
- [Driver 2]
- ...

## Considered Options

### Option 1: [Name]

**Pros:**
- ✅ [Pro 1]
- ✅ [Pro 2]

**Cons:**
- ❌ [Con 1]
- ❌ [Con 2]

**Verdict:** [Selected | Rejected] - [Reason]

## Decision Outcome

**Chosen Option:** [Option name]

[Explanation of why this option was chosen]

### Consequences

**Positive:**
- ✅ [Positive consequence 1]

**Negative:**
- ❌ [Negative consequence 1]

**Neutral:**
- 🔄 [Neutral consequence 1]

## Links

- [Related ADR 1](./xxx.md)
- [External reference 1](https://...)
```

## Status Definitions

- **Proposed:** Decision is under consideration
- **Accepted:** Decision has been made and is being implemented
- **Deprecated:** Decision is no longer relevant
- **Superseded:** Decision has been replaced by another ADR

## Contributing

When making significant architectural decisions:

1. Create a new ADR using the template above
2. Number it sequentially (ADR-XXX)
3. Discuss in pull request or issue
4. Update status once decision is made
5. Link related ADRs and issues
