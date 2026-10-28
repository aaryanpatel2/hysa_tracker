#!/usr/bin/env python3
"""
Test script for HYSA Tracker notification system.
Tests all notification modes and triggers without running the full scraper.
"""

from datetime import datetime
import os

# Mock the notification function
def should_send_notification(main_tracked_rates, last_rates, other_rates, mode, test_date=None):
    """
    Test version of notification checker with date override capability
    """
    now = test_date if test_date else datetime.now()
    
    # Configuration
    SIGNIFICANT_DROP_THRESHOLD = 0.15
    SIGNIFICANT_RISE_THRESHOLD = 0.20
    
    if mode == "never":
        return False, "Notification mode set to 'never'"
    
    if mode == "always":
        return True, "Always mode - sending notification"
    
    if mode == "monthly":
        if now.day == 1:
            return True, "Monthly digest (1st of month)"
        return False, "Not the 1st of the month"
    
    if mode == "weekly":
        if now.weekday() == 6:  # Sunday = 6
            return True, "Weekly digest (Sunday)"
        return False, "Not Sunday"
    
    # Smart mode
    if mode == "smart":
        reasons = []
        
        # Check for significant drops
        for bank, current_rate in main_tracked_rates.items():
            if bank in last_rates:
                drop = last_rates[bank] - current_rate
                if drop >= SIGNIFICANT_DROP_THRESHOLD:
                    reasons.append(f"🔴 {bank} dropped {drop:.2f}% (threshold: {SIGNIFICANT_DROP_THRESHOLD}%)")
        
        # Check for competitors rising significantly
        if main_tracked_rates:
            best_tracked_rate = max(main_tracked_rates.values())
            for bank, rate in other_rates.items():
                if rate >= best_tracked_rate + SIGNIFICANT_RISE_THRESHOLD:
                    diff = rate - best_tracked_rate
                    reasons.append(f"🔴 {bank} now {diff:.2f}% above your best (threshold: {SIGNIFICANT_RISE_THRESHOLD}%)")
        
        # Monthly report on 1st
        if now.day == 1:
            reasons.append("🟢 Monthly comprehensive report (1st of month)")
        
        # Weekly digest on Sunday (unless also 1st)
        if now.weekday() == 6 and now.day != 1:
            reasons.append("🟡 Weekly digest (Sunday)")
        
        if reasons:
            return True, " | ".join(reasons)
        
        return False, "No significant changes detected"
    
    return True, f"Unknown mode '{mode}' - defaulting to always"


def run_tests():
    """Run comprehensive notification tests"""
    print("\n" + "=" * 70)
    print("🧪 HYSA TRACKER - NOTIFICATION SYSTEM TEST SUITE")
    print("=" * 70)
    
    # Mock data
    mock_tracked_rates = {
        "Barclays": 3.85,
        "Marcus": 3.65,
        "Apple": 3.65,
        "Ally": 3.30,
        "Sofi": 3.30
    }
    
    mock_last_rates_no_change = {
        "Barclays": 3.85,
        "Marcus": 3.65,
        "Apple": 3.65,
        "Ally": 3.30,
        "Sofi": 3.30
    }
    
    mock_last_rates_with_drop = {
        "Barclays": 3.85,
        "Marcus": 3.85,  # ⚠️ Dropped from 3.85% to 3.65% = 0.20% drop
        "Apple": 3.65,
        "Ally": 3.30,
        "Sofi": 3.30
    }
    
    mock_other_rates_normal = {
        "UFB Direct": 4.00,
        "My Banking Direct": 3.95,
        "Bread Savings": 3.90
    }
    
    mock_other_rates_high_competitor = {
        "UFB Direct": 4.11,  # ⚠️ 0.26% above best (3.85)
        "My Banking Direct": 4.05,
        "Bread Savings": 4.00
    }
    
    # Test scenarios
    scenarios = [
        {
            "name": "1. ALWAYS Mode (any day)",
            "mode": "always",
            "date": datetime(2026, 1, 8, 14, 0),  # Wednesday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "2. NEVER Mode",
            "mode": "never",
            "date": datetime(2026, 1, 8, 14, 0),
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_with_drop,  # Even with drop!
            "other_rates": mock_other_rates_high_competitor,
        },
        {
            "name": "3. WEEKLY Mode - Sunday",
            "mode": "weekly",
            "date": datetime(2026, 1, 12, 14, 0),  # Sunday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "4. WEEKLY Mode - Wednesday (not Sunday)",
            "mode": "weekly",
            "date": datetime(2026, 1, 8, 14, 0),  # Wednesday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "5. MONTHLY Mode - 1st of month",
            "mode": "monthly",
            "date": datetime(2026, 1, 1, 14, 0),  # 1st
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "6. MONTHLY Mode - Mid-month",
            "mode": "monthly",
            "date": datetime(2026, 1, 15, 14, 0),  # 15th
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "7. SMART Mode - Immediate Alert (significant drop)",
            "mode": "smart",
            "date": datetime(2026, 1, 8, 14, 0),  # Wednesday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_with_drop,  # Marcus dropped 0.20%
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "8. SMART Mode - Immediate Alert (competitor rise)",
            "mode": "smart",
            "date": datetime(2026, 1, 8, 14, 0),  # Wednesday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_high_competitor,  # UFB 0.26% above
        },
        {
            "name": "9. SMART Mode - Weekly Digest (Sunday, no alerts)",
            "mode": "smart",
            "date": datetime(2026, 1, 12, 14, 0),  # Sunday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "10. SMART Mode - Monthly Report (1st of month)",
            "mode": "smart",
            "date": datetime(2026, 2, 1, 14, 0),  # Sunday + 1st (Feb 1, 2026)
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,
            "other_rates": mock_other_rates_normal,
        },
        {
            "name": "11. SMART Mode - No triggers (regular weekday)",
            "mode": "smart",
            "date": datetime(2026, 1, 8, 14, 0),  # Wednesday
            "rates": mock_tracked_rates,
            "last_rates": mock_last_rates_no_change,  # No change
            "other_rates": mock_other_rates_normal,  # No high competitors
        },
    ]
    
    # Run tests
    for scenario in scenarios:
        print(f"\n📋 {scenario['name']}")
        print(f"   Date: {scenario['date'].strftime('%Y-%m-%d (%A)')}")
        print(f"   Mode: '{scenario['mode']}'")
        
        should_notify, reason = should_send_notification(
            scenario['rates'],
            scenario['last_rates'],
            scenario['other_rates'],
            scenario['mode'],
            scenario['date']
        )
        
        status = "✅ SEND NOTIFICATION" if should_notify else "🔕 SUPPRESS"
        print(f"   Result: {status}")
        print(f"   Reason: {reason}")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
    
    print("\n📝 Summary:")
    print("   • ALWAYS mode: Sends every time")
    print("   • NEVER mode: Never sends")
    print("   • WEEKLY mode: Only on Sundays")
    print("   • MONTHLY mode: Only on 1st of month")
    print("   • SMART mode (RECOMMENDED):")
    print("      - 🔴 Immediate alerts for drops ≥0.15% or competitor rises ≥0.20%")
    print("      - 🟡 Weekly digest every Sunday")
    print("      - 🟢 Monthly report on 1st of month")
    
    print("\n🔧 To change notification mode, set in .env:")
    print("   NOTIFICATION_MODE=smart  # Recommended")
    print("\n")


if __name__ == "__main__":
    run_tests()
