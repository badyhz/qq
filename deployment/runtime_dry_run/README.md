# Quant System Dry-run Runtime — Server Deployment Guide

## Overview

This is a **dry-run only** deployment. No real trading, no real testnet submit.

## Quick Start

```bash
cp env.example .env
PYTHONPATH=. python3 scripts/run_system_dry_run_e2e.py
```

## Safety

- Real trading: **NOT ALLOWED**
- Testnet submit: **NOT ALLOWED**
- All orders are simulated
- All alerts are dry-run only
