import argparse
import base64
import getpass
import json
import os
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
except ImportError:
    sys.exit("Missing dependency. Install it with: pip install cryptography\n"
             "(Arch/Manjaro: sudo pacman -S python-cryptography)")

AMBIGUOUS = "O0oIl1|"
SALT_LEN = 16

if os.name == "nt":
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "passgen"
else:
    DATA_DIR = Path.home() / ".local/share/passgen"
VAULT_FILE = DATA_DIR / "vault.bin"


# ---------- encrypted vault ----------

def _key(master, salt):
    kdf = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1)
    return base64.urlsafe_b64encode(kdf.derive(master.encode()))

def _load(master):
    if not VAULT_FILE.exists():
        return [], secrets.token_bytes(SALT_LEN)
    raw = VAULT_FILE.read_bytes()
    salt, token = raw[:SALT_LEN], raw[SALT_LEN:]
    try:
        data = Fernet(_key(master, salt)).decrypt(token)
    except InvalidToken:
        raise ValueError("Wrong master password, or the vault file is damaged.")
    return json.loads(data), salt

def _save(entries, master, salt):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    token = Fernet(_key(master, salt)).encrypt(json.dumps(entries).encode())
    tmp = VAULT_FILE.with_suffix(".tmp")
    tmp.write_bytes(salt + token)
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    os.replace(tmp, VAULT_FILE)

def ask_master(confirm=False):
    pw = getpass.getpass("Master password: ")
    if not pw:
        raise ValueError("Master password can't be empty.")
    if confirm and getpass.getpass("Repeat master password: ") != pw:
        raise ValueError("Passwords didn't match.")
    return pw

def log_entry(site, username, password):
    is_new = not VAULT_FILE.exists()
    if is_new:
        print("Creating a new vault. If you forget this master password, "
              "the data is gone for good.")
    master = ask_master(confirm=is_new)
    entries, salt = _load(master)
    entries.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "site": site,
        "username": username,
        "password": password,
    })
    _save(entries, master, salt)
    print(f"Saved to {VAULT_FILE}")

def view_vault():
    if not VAULT_FILE.exists():
        print("No vault yet. Save an entry first.")
        return
    entries, _ = _load(ask_master())
    if not entries:
        print("Vault is empty.")
    for e in entries:
        print(f"{e['date']} | {e['site']} | {e['username']} | {e['password']}")


# ---------- generator ----------

def generate_password(length=16, upper=True, lower=True, digits=True,
                      symbols=True, exclude_ambiguous=False, exclude_chars=""):
    pools = []
    if lower:   pools.append(string.ascii_lowercase)
    if upper:   pools.append(string.ascii_uppercase)
    if digits:  pools.append(string.digits)
    if symbols: pools.append("!@#$%^&*()-_=+[]{};:,.<>?")

    if not pools:
        raise ValueError("Enable at least one character type.")

    banned = set(exclude_chars) | (set(AMBIGUOUS) if exclude_ambiguous else set())
    filtered = ["".join(c for c in p if c not in banned) for p in pools]
    if any(not p for p in filtered):
        raise ValueError("Your exclusions removed every character of an enabled type.")
    pools = filtered

    if length < len(pools):
        raise ValueError(f"Length must be at least {len(pools)} for the selected options.")

    password = [secrets.choice(p) for p in pools]
    all_chars = "".join(pools)
    password += [secrets.choice(all_chars) for _ in range(length - len(password))]

    secrets.SystemRandom().shuffle(password)
    return "".join(password)


# ---------- interfaces ----------

def ask_yn(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    ans = input(f"{prompt} {suffix}: ").strip().lower()
    return default if not ans else ans.startswith("y")

def interactive():
    try:
        if input("[G]enerate or [V]iew saved? [G]: ").strip().lower().startswith("v"):
            view_vault()
        else:
            length = int(input("Length [16]: ") or 16)
            count = int(input("How many [1]: ") or 1)
            upper = ask_yn("Uppercase?")
            lower = ask_yn("Lowercase?")
            digits = ask_yn("Digits?")
            symbols = ask_yn("Symbols?")
            no_amb = ask_yn("Exclude look-alike characters?", default=False)
            exclude = input("Characters to exclude (blank for none): ")
            print()
            passwords = [generate_password(length, upper, lower, digits, symbols, no_amb, exclude)
                         for _ in range(count)]
            for p in passwords:
                print(p)
            if count == 1 and ask_yn("\nSave to vault?", default=False):
                site = input("Site/app: ")
                username = input("Username/email: ")
                log_entry(site, username, passwords[0])
    except (ValueError, KeyboardInterrupt) as e:
        print(f"\nError: {e}")
    input("\nPress Enter to close...")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive()
    else:
        parser = argparse.ArgumentParser(description="Password generator")
        parser.add_argument("-l", "--length", type=int, default=16)
        parser.add_argument("-n", "--count", type=int, default=1)
        parser.add_argument("--no-upper", action="store_true")
        parser.add_argument("--no-lower", action="store_true")
        parser.add_argument("--no-digits", action="store_true")
        parser.add_argument("--no-symbols", action="store_true")
        parser.add_argument("--no-ambiguous", action="store_true", help="Exclude look-alike chars like O/0, l/1")
        parser.add_argument("--exclude", default="", help="Specific characters to exclude")
        parser.add_argument("--site", default="", help="Save the password to the vault under this site")
        parser.add_argument("--user", default="", help="Username to save with it")
        parser.add_argument("--view", action="store_true", help="Show saved entries")
        args = parser.parse_args()

        try:
            if args.view:
                view_vault()
            else:
                for _ in range(args.count):
                    pw = generate_password(
                        length=args.length,
                        upper=not args.no_upper,
                        lower=not args.no_lower,
                        digits=not args.no_digits,
                        symbols=not args.no_symbols,
                        exclude_ambiguous=args.no_ambiguous,
                        exclude_chars=args.exclude,
                    )
                    print(pw)
                    if args.site:
                        log_entry(args.site, args.user, pw)
        except ValueError as e:
            sys.exit(f"Error: {e}")
