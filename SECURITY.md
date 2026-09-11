# Security Policy

## Reporting a vulnerability

Email **gritli.tarek66@gmail.com** with a description of the issue, steps to
reproduce, and its potential impact. Please do not open a public GitHub issue
for security reports.

You'll get an acknowledgment within **3 business days**. If confirmed, a fix is
targeted within **30 days** for high/critical severity, 90 days otherwise,
depending on complexity. You'll be credited in the release notes unless you'd
rather stay anonymous.

## Scope

In scope: the gateway (`apps/gateway`), agents/fix-engine (`apps/agents`), CLI
(`apps/cli`), and shared packages (`packages/`) in this repository.

Out of scope: vulnerabilities in third-party managed services this project
depends on (GCP, Neon, Qdrant Cloud, Redis Cloud, GitHub, Anthropic, Stripe) —
report those directly to the vendor.

## Supported versions

This project deploys continuously from `main`; only the latest deployed
revision is supported. There are no maintained release branches.

## Safe harbor

Good-faith security research performed against your own account/data, without
accessing other users' data or disrupting the service, will not result in
legal action.
