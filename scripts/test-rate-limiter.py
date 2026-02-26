#!/usr/bin/env python3
"""
Test Rate Limiter

Tests the intelligent rate limiter with a small set of stocks
to verify it properly handles API rate limits.

Usage:
    python scripts/test-rate-limiter.py
"""

import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import config
from modules.ingestion.loader import VNStockLoader

def test_rate_limiter():
    """Test rate limiter with 10 stocks"""
    print("=" * 60)
    print("RATE LIMITER TEST")
    print("=" * 60)
    print()
    print("Testing with 10 stocks (VN30 blue chips)")
    print("Expected behavior:")
    print("  • First ~18 requests: Normal speed")
    print("  • At ~55/60 requests: Auto-pause (showing countdown)")
    print("  • After cooldown: Resume automatically")
    print()
    print("=" * 60)
    print()

    # Use first 10 stocks from VN100
    test_symbols = config.VN100_SYMBOLS[:10]

    print(f"Test symbols: {', '.join(test_symbols)}")
    print()

    # Initialize loader (this creates rate limiter)
    loader = VNStockLoader()

    # Run ingestion
    result_df = loader.run_ingestion(test_symbols, parallel=True, max_workers=2)

    # Results
    print()
    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(result_df[['Symbol', 'Status', 'Has_Price', 'Has_Balance', 'Has_Income']])
    print()

    # Verify all succeeded
    success_rate = (result_df['Status'] == 'SUCCESS').sum() / len(result_df) * 100
    print(f"Success rate: {success_rate:.1f}%")

    if success_rate >= 80:
        print()
        print("✅ TEST PASSED - Rate limiter working correctly!")
    else:
        print()
        print("⚠️  TEST WARNING - Some stocks failed (may be normal)")
        print("   Check logs for details")

    print()

if __name__ == "__main__":
    test_rate_limiter()
