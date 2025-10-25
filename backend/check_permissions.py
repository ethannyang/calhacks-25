"""
Check macOS permissions for screen capture
"""

import Quartz
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID
from Quartz import CGWindowListCreateImage, CGRectNull, kCGWindowListOptionIncludingWindow
from Quartz import kCGWindowImageDefault, CoreGraphics

def check_permissions():
    print("=== macOS Screen Capture Permission Check ===\n")

    # Check 1: Can we list windows? (Accessibility)
    print("1. Testing Window List (Accessibility)...")
    try:
        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
        if window_list and len(window_list) > 0:
            print(f"   ✅ SUCCESS: Can list {len(window_list)} windows")
            print(f"   → Accessibility permissions: GRANTED")
        else:
            print("   ❌ FAILED: Cannot list windows")
            print("   → Accessibility permissions: DENIED")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        print("   → Accessibility permissions: DENIED")

    # Check 2: Can we capture screen? (Screen Recording)
    print("\n2. Testing Screen Capture (Screen Recording)...")
    try:
        cg_image = CoreGraphics.CGDisplayCreateImage(CoreGraphics.CGMainDisplayID())

        if cg_image:
            width = CoreGraphics.CGImageGetWidth(cg_image)
            height = CoreGraphics.CGImageGetHeight(cg_image)

            if width > 0 and height > 0:
                print(f"   ✅ SUCCESS: Captured {width}x{height} screenshot")
                print(f"   → Screen Recording permissions: GRANTED")
            else:
                print(f"   ❌ FAILED: Invalid dimensions {width}x{height}")
                print("   → Screen Recording permissions: DENIED")
        else:
            print("   ❌ FAILED: Cannot capture screen")
            print("   → Screen Recording permissions: DENIED")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        print("   → Screen Recording permissions: DENIED")

    # Check 3: Can we capture a specific window?
    print("\n3. Testing Window Capture (Screen Recording)...")
    try:
        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)

        # Find first visible window
        test_window_id = None
        for window in window_list:
            window_id = window.get('kCGWindowNumber', 0)
            app_name = window.get('kCGWindowOwnerName', '')
            bounds = window.get('kCGWindowBounds', {})
            width = int(bounds.get('Width', 0))
            height = int(bounds.get('Height', 0))

            if app_name and width > 200 and height > 200:
                test_window_id = window_id
                print(f"   Testing with window: {app_name} ({window_id})")
                break

        if test_window_id:
            cg_image = CGWindowListCreateImage(
                CGRectNull,
                kCGWindowListOptionIncludingWindow,
                test_window_id,
                kCGWindowImageDefault
            )

            if cg_image:
                width = CoreGraphics.CGImageGetWidth(cg_image)
                height = CoreGraphics.CGImageGetHeight(cg_image)

                if width > 0 and height > 0:
                    print(f"   ✅ SUCCESS: Captured {width}x{height} window")
                    print(f"   → Screen Recording permissions: GRANTED")
                else:
                    print(f"   ❌ FAILED: Invalid window dimensions")
                    print("   → Screen Recording permissions: DENIED")
            else:
                print("   ❌ FAILED: Cannot capture window")
                print("   → Screen Recording permissions: DENIED")
        else:
            print("   ⚠️  No suitable test window found")

    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        print("   → Screen Recording permissions: DENIED")

    # Final verdict
    print("\n" + "="*50)
    print("NEXT STEPS:")
    print("="*50)
    print("\nIf Screen Recording is DENIED:")
    print("1. Run: open 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'")
    print("2. Click the '+' button or toggle to add your terminal app")
    print("3. IMPORTANT: Completely quit and restart your terminal")
    print("4. Re-run this script to verify")
    print("\nTerminal apps to look for:")
    print("  - Terminal.app")
    print("  - iTerm2")
    print("  - Visual Studio Code")
    print("  - Python (or python3)")

if __name__ == "__main__":
    check_permissions()
