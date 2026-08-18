"""Test environment configuration loaded before application imports."""

import hashlib
import os

TEST_SALT = bytes.fromhex("00112233445566778899aabbccddeeff")
TEST_PASSWORD = "correct-horse-battery-staple"
TEST_HASH = hashlib.scrypt(
    TEST_PASSWORD.encode(), salt=TEST_SALT, n=2**14, r=8, p=1
).hex()

os.environ["SIM_ADMIN_USERNAME"] = "admin"
os.environ["SIM_ADMIN_PASSWORD_HASH"] = f"{TEST_SALT.hex()}:{TEST_HASH}"
os.environ["SIM_ADMIN_SESSION_SECRET"] = "test-session-secret-not-for-production"
os.environ["SIM_ADMIN_SECURE_COOKIE"] = "false"
os.environ["SIM_ADMIN_AUDIT_DB"] = ":memory:"
