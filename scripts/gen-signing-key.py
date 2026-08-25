#!/usr/bin/env python3
"""gen-signing-key.py - create the Kavach evidence signing keypair (ed25519).

The PRIVATE key must live OUTSIDE the repo (default ~/.kavach-signing/).
The PUBLIC key is what you publish so anyone can verify packet signatures.

Usage:
    python3 scripts/gen-signing-key.py [--dir ~/.kavach-signing]
Refuses to overwrite existing keys.
"""
import argparse, os, sys

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("cryptography package missing: uv pip install cryptography")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.expanduser("~/.kavach-signing"))
    args = ap.parse_args()
    os.makedirs(args.dir, exist_ok=True)
    priv_path = os.path.join(args.dir, "signing_private.pem")
    pub_path = os.path.join(args.dir, "signing_public.pem")
    for p in (priv_path, pub_path):
        if os.path.exists(p):
            print(f"[ERROR] {p} exists, refusing to overwrite. Delete it first if you really want a new key.")
            sys.exit(1)
    key = Ed25519PrivateKey.generate()
    with open(priv_path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
    with open(pub_path, "wb") as f:
        f.write(key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
    print("keypair written:")
    print("  private:", priv_path, "(keep secret, never commit)")
    print("  public :", pub_path, "(publish this for signature verification)")
    print()
    print(open(pub_path).read().strip())


if __name__ == "__main__":
    main()