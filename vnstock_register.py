"""
Vnstock API Key Registration Helper

Hướng dẫn đăng ký FREE API key để tăng tốc 3x và truy cập 8 kỳ báo cáo tài chính.

Usage:
    python vnstock_register.py

Hoặc set API key trực tiếp trong .env:
    VNSTOCK_API_KEY=vnstock_YOUR_KEY_HERE
"""

import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def check_api_key():
    """Check if API key is already configured"""
    api_key = os.environ.get('VNSTOCK_API_KEY')
    if api_key and api_key.startswith('vnstock_'):
        return api_key
    return None

def register_interactive():
    """Interactive API key registration"""
    try:
        from vnstock import register_user
        print("=" * 60)
        print("  VNSTOCK API KEY REGISTRATION")
        print("=" * 60)
        print()
        print("📝 Hướng dẫn:")
        print("  1. Truy cập: https://vnstocks.com/login")
        print("  2. Đăng nhập bằng Google")
        print("  3. Copy API key từ dashboard")
        print("  4. Paste vào đây")
        print()
        print("💎 Benefits (FREE):")
        print("  - 60 requests/minute (vs 20 guest)")
        print("  - 8 quarters financial data (vs 4 guest)")
        print("  - Priority KBS data source")
        print()
        print("=" * 60)
        print()

        # Interactive registration
        register_user()

        print()
        print("✅ Registration successful!")
        print()
        print("💡 Tip: Add to .env file for persistent config:")
        print("   VNSTOCK_API_KEY=vnstock_YOUR_KEY_HERE")
        print()

    except ImportError:
        print("❌ Error: vnstock package not found")
        print("   Please upgrade: pip install git+https://github.com/thinh-vu/vnstock@main")
    except Exception as e:
        print(f"❌ Error during registration: {e}")

def register_direct(api_key: str):
    """Direct API key registration"""
    try:
        from vnstock import register_user
        register_user(api_key=api_key)
        print(f"✅ API key registered: {api_key[:20]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    # Check existing API key
    existing_key = check_api_key()
    if existing_key:
        print(f"✅ API key already configured: {existing_key[:20]}...")
        print()
        print("To re-register, remove VNSTOCK_API_KEY from .env first.")
        return

    # Check command line argument
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        if api_key.startswith('vnstock_'):
            register_direct(api_key)
        else:
            print("❌ Invalid API key format. Must start with 'vnstock_'")
    else:
        # Interactive mode
        register_interactive()

if __name__ == '__main__':
    main()
