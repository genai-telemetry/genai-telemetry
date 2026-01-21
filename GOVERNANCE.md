# GenAI Telemetry Governance

## Overview

GenAI Telemetry is an open source project that provides platform-agnostic observability for GenAI/LLM applications. This document describes how the project is governed.

## Project Mission

To provide a vendor-neutral, production-grade observability SDK that enables organizations to monitor, trace, and understand their GenAI applications across any observability platform.

## Roles and Responsibilities

### Users

Users are community members who have a need for the project. Anyone can be a user; there are no special requirements.

### Contributors

Contributors are community members who contribute in concrete ways to the project. Anyone can become a contributor by:

- Reporting bugs
- Suggesting features
- Improving documentation
- Submitting code changes
- Helping other users

### Committers

Committers are contributors who have earned the ability to modify source code, documentation, or other technical artifacts. Committers are responsible for:

- Reviewing and approving pull requests
- Participating in technical discussions
- Mentoring contributors
- Ensuring code quality

**Current Committers:**

| Name | GitHub | Organization |
|------|--------|--------------|
| Kamal Singh Bisht | @kamalbisht | Capital One |

### Maintainers

Maintainers are committers who have been granted additional responsibilities including:

- Setting project direction and priorities
- Making final decisions on technical matters
- Managing releases
- Approving new committers
- Representing the project externally

**Current Maintainers:**

| Name | GitHub | Organization | Role |
|------|--------|--------------|------|
| Kamal Singh Bisht | @kamalbisht | Capital One | Lead Maintainer |

## Technical Steering Committee (TSC)

For LF AI & Data Incubation level, a Technical Steering Committee will be formed with:

- Minimum 3 members from at least 2 different organizations
- A designated TSC Chair
- Quarterly public meetings
- Meeting notes published within 1 week

### TSC Responsibilities

- Technical direction of the project
- Project roadmap decisions
- Release management
- Resolving technical disputes
- Approving architectural changes

## Decision Making

### Consensus-Based Decision Making

The project aims to operate by consensus of the maintainers. When consensus cannot be reached, the following process applies:

1. **Discussion**: Open discussion on GitHub issue/PR for minimum 72 hours
2. **Voting**: If consensus not reached, maintainers vote
3. **Majority**: Simple majority of maintainers required
4. **Tie-breaking**: Lead Maintainer has tie-breaking vote

### Types of Decisions

| Decision Type | Process |
|---------------|---------|
| Bug fixes | Single maintainer approval |
| Minor features | Two maintainer approvals |
| Major features | RFC + maintainer consensus |
| Breaking changes | RFC + community feedback + TSC approval |
| Governance changes | TSC approval + 2-week comment period |

## RFC Process

For significant changes, a Request for Comments (RFC) process is used:

1. Create RFC document in `rfcs/` directory
2. Open PR for discussion (minimum 2 weeks)
3. Address feedback and iterate
4. TSC vote on approval
5. If approved, implementation can proceed

## Adding Committers

New committers are nominated by existing committers/maintainers based on:

- Sustained, high-quality contributions
- Understanding of project goals
- Collaborative engagement with community
- Adherence to code of conduct

Process:
1. Nomination by existing committer
2. Discussion among maintainers (private)
3. Unanimous approval required
4. Invitation extended
5. Added to MAINTAINERS.md

## Removing Committers/Maintainers

Removal may occur due to:
- Inactivity (12+ months without contribution)
- Repeated code of conduct violations
- Voluntary resignation

Process:
1. Private discussion among maintainers
2. Outreach to individual (if possible)
3. Majority vote of remaining maintainers
4. Move to emeritus status in MAINTAINERS.md

## Meetings

- **Community Calls**: Monthly, open to all
- **TSC Meetings**: Quarterly, public
- **Meeting Notes**: Published in `meetings/` directory

## Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Slack**: Real-time collaboration (via LF AI Slack)
- **Mailing List**: Announcements, governance discussions

## Code of Conduct

All project participants must adhere to the [Code of Conduct](CODE_OF_CONDUCT.md). Violations should be reported to conduct@genai-telemetry.io.

## Licensing

All contributions must be made under the Apache License 2.0. By contributing, you agree that your contributions will be licensed under the same license.

## Changes to Governance

Changes to this governance document require:

1. Proposal via pull request
2. 2-week public comment period
3. TSC approval
4. No unresolved objections from maintainers

---

*This governance model is designed to evolve as the project grows and may be updated to meet LF AI & Data Foundation requirements.*
