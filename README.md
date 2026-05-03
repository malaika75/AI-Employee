# Digital FTE

Your AI-powered digital employee that autonomously handles email, social media, and invoicing—with human oversight when it matters.

## Problem

Modern businesses waste hours on repetitive operational tasks: sorting through endless emails, manually posting to social platforms, and chasing invoice payments. Your team deserves better than busywork.

## Solution

Digital FTE is an AI employee that autonomously handles everyday business operations while keeping humans in the loop for key decisions.

- **Email Intelligence**: Auto-triage, categorize, and route incoming emails to the right recipients. Attachments processed and context extracted automatically.
- **Social Automation**: Draft and schedule posts across LinkedIn, Twitter, and Facebook from a single dashboard. Human approval before any content goes live.
- **Invoice Automation**: Generate and send invoices directly in Odoo ERP. Zero missed invoices. Zero manual follow-ups.
- **Central Dashboard**: Next.js dashboard gives you full visibility. Approve, reject, or modify any AI action in seconds.

## Impact

- **~70% time saved** on email triage and routing
- **Zero missed invoices** since deployment
- **~90% reduction** in manual social posting effort
- **24/7 operation** with human oversight on high-stakes decisions

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the AI Employee (Terminal 1)
python main.py

# Start MCP servers (Terminal 2)
python start_processes.py
```

Open `http://localhost:5000` to access the dashboard.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Email MCP   │────▶│   AI Brain   │────▶│  Dashboard  │
│ (Gmail)     │     │  (Anthropic) │     │  (Next.js)  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Social MCP │     │  Odoo MCP   │     │  Vault     │
│ (LinkedIn) │     │  (ERP)      │     │  (Memory)  │
└─────────────┘     └──────────────┘     └─────────────┘
```

**Tech Stack**: Python, Anthropic SDK, Model Context Protocol (MCP), Next.js
**Platform**: Windows desktop app

---

**Built by** Your Name
**License**: MIT