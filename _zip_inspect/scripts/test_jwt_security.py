#!/usr/bin/env python3
"""
JWT 安全增强功能测试脚本

验证内容：
1. 密钥生成脚本能够生成符合要求的安全密钥（>=256 位）
2. 未配置密钥时，生产环境应用启动失败
3. 配置有效密钥时，系统正常工作
4. 开发环境未配置密钥时显示警告但不阻止启动
"""

import os
import sys
import subprocess

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

PASS = "[PASS]"
FAIL = "[FAIL]"


def test_generate_jwt_secret():
    """Test JWT key generation script"""
    print("\n=== Test 1: JWT key generation script ===")

    result = subprocess.run(
        [sys.executable, "scripts/generate_jwt_secret.py"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    if result.returncode != 0:
        print(f"  {FAIL} Key generation script failed")
        print(f"  stderr: {result.stderr}")
        return False

    # The key is on the first line of stdout
    secret = result.stdout.strip().split("\n")[0].strip()
    print(f"  Generated key: {secret[:20]}... ({len(secret)} chars)")

    # Verify key length (should be 64 hex chars = 32 bytes)
    if len(secret) != 64:
        print(f"  {FAIL} Key length should be 64 chars, got {len(secret)}")
        return False

    # Verify key is valid hex
    try:
        int(secret, 16)
        print(f"  {PASS} Key format is correct (hex, 64 chars)")
    except ValueError:
        print(f"  {FAIL} Key is not a valid hex string")
        return False

    # Test custom length parameter
    result_48 = subprocess.run(
        [sys.executable, "scripts/generate_jwt_secret.py", "--length", "48"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    secret_48 = result_48.stdout.strip().split("\n")[0]
    if len(secret_48) == 96:  # 48 bytes = 96 hex chars
        print(f"  {PASS} Custom length supported (48 bytes -> 96 chars)")
    else:
        print(f"  {FAIL} Custom length parameter invalid")
        return False

    # Test --env-format parameter
    result_env = subprocess.run(
        [sys.executable, "scripts/generate_jwt_secret.py", "--env-format"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    env_output = result_env.stdout.strip().split("\n")[0]
    if env_output.startswith("JWT_SECRET_KEY="):
        print(f"  {PASS} --env-format parameter output is correct")
    else:
        print(f"  {FAIL} --env-format parameter output format error")
        return False

    # Test key less than 32 bytes should fail
    result_short = subprocess.run(
        [sys.executable, "scripts/generate_jwt_secret.py", "--length", "16"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    if result_short.returncode != 0:
        print(f"  {PASS} Correctly rejects key length < 32 bytes")
    else:
        print(f"  {FAIL} Should reject key length < 32 bytes")
        return False

    print(f"\n  {PASS} Test 1 passed")
    return True


def test_production_without_key():
    """Test that production environment fails startup without key"""
    print("\n=== Test 2: Production environment without key ===")

    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["JWT_SECRET_KEY"] = ""  # Empty value

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'backend'); "
                "from app.config import Settings; "
                "s = Settings(); "
                "s.validate_jwt_security()",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )

        stderr_lower = result.stderr.lower()
        has_error = (
            "security" in stderr_lower
            or "must" in stderr_lower
            or "error" in stderr_lower
        )
        if result.returncode != 0 and has_error:
            print(f"  {PASS} Production without key correctly throws error")
            print(
                f"  Error message: "
                f"{result.stderr.split('RuntimeError:')[-1].strip()[:100]}..."
            )
            print(f"\n  {PASS} Test 2 passed")
            return True
        else:
            print(
                f"  {FAIL} Should throw security error "
                f"but returned: {result.returncode}"
            )
            if result.stderr:
                print(f"  stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"  Test exception: {e}")
        return False


def test_production_with_placeholder():
    """Test that production environment fails startup with placeholder key"""
    print("\n=== Test 3: Production environment with placeholder key ===")

    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["JWT_SECRET_KEY"] = "change-this-to-a-secure-random-secret-key-in-production"

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'backend'); "
                "from app.config import Settings; "
                "s = Settings(); "
                "s.validate_jwt_security()",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )

        stderr_lower = result.stderr.lower()
        has_error = (
            "security" in stderr_lower
            or "must" in stderr_lower
            or "error" in stderr_lower
        )
        if result.returncode != 0 and has_error:
            print(f"  {PASS} Production with placeholder correctly throws error")
            print(f"\n  {PASS} Test 3 passed")
            return True
        else:
            print(
                f"  {FAIL} Should throw security error "
                f"but returned: {result.returncode}"
            )
            return False

    except Exception as e:
        print(f"  Test exception: {e}")
        return False


def test_development_without_key():
    """Test development env shows warning but allows startup"""
    print("\n=== Test 4: Development environment without key ===")

    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["JWT_SECRET_KEY"] = ""  # Empty value

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'backend'); "
                "from app.config import Settings; "
                "s = Settings(); "
                "s.validate_jwt_security(); "
                "print('Development mode allows empty key')",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )

        # Dev env allows empty key (warning but continues)
        if "Development mode allows empty key" in result.stdout:
            print(f"  {PASS} Development without key allows continuation")
            stderr_lower = result.stderr.lower()
            if "warning" in stderr_lower or "warn" in stderr_lower:
                print(f"  {PASS} Security warning was shown")
            print(f"\n  {PASS} Test 4 passed")
            return True
        else:
            print(f"  {FAIL} Development should allow empty key")
            if result.stderr:
                print(f"  stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"  Test exception: {e}")
        return False


def test_production_with_valid_key():
    """Test that production environment works correctly with valid key"""
    print("\n=== Test 5: Production environment with valid key ===")

    # Generate a valid key
    result = subprocess.run(
        [sys.executable, "scripts/generate_jwt_secret.py"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    valid_secret = result.stdout.strip().split("\n")[0]

    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["JWT_SECRET_KEY"] = valid_secret

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, 'backend'); "
                "from app.config import Settings; "
                "s = Settings(); "
                "s.validate_jwt_security(); "
                "print('Production mode with valid key works')",
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
        )

        if "Production mode with valid key works" in result.stdout:
            print(f"  {PASS} Production with valid key works correctly")
            print(f"\n  {PASS} Test 5 passed")
            return True
        else:
            print(f"  {FAIL} Production with valid key should run normally")
            if result.stderr:
                print(f"  stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"  Test exception: {e}")
        return False


def main():
    print("=" * 60)
    print("JWT Security Enhancement Tests")
    print("=" * 60)

    tests = [
        test_generate_jwt_secret,
        test_production_without_key,
        test_production_with_placeholder,
        test_development_without_key,
        test_production_with_valid_key,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for i, (test, result) in enumerate(zip(tests, results)):
        status = "PASSED" if result else "FAILED"
        print(f"Test {i + 1}: {test.__doc__} -> {status}")

    passed = sum(results)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nAll tests passed! JWT security enhancements work correctly.")
        return 0
    else:
        print(f"\n{total - passed} tests failed, please check the issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
