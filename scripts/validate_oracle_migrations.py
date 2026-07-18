#!/usr/bin/env python3
"""Validate deterministic PostgreSQL-to-Oracle migration parity."""

from __future__ import annotations

from generate_oracle_migrations import main

if __name__ == "__main__":
    raise SystemExit(main(["--check"]))
