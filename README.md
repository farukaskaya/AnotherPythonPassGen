# passgen

A small cross-platform (Linux and Windows) password generator written in Python, with an optional **encrypted vault** for saving generated passwords next to their site and username.

Passwords are generated with Python's [`secrets`](https://docs.python.org/3/library/secrets.html) module (cryptographically secure), not `random`.

> **Status: learning project.** The vault is a hand-built convenience feature, not an audited password manager. For passwords that really matter (email, banking, anything account recovery depends on), use [KeePassXC](https://keepassxc.org/) or another established tool. See [Security notes](#security-notes).

## Features

- Adjustable length and number of passwords
- Toggle uppercase, lowercase, digits and symbols
- Exclude look-alike characters (`O 0 o I l 1 |`)
- Exclude any custom characters you choose
- Guarantees at least one character from every enabled type
- Refuses to run (instead of silently weakening the password) if your exclusions remove an entire character type
- Interactive menu mode (no arguments), so it can be launched from an application menu
- Command-line mode for scripting
- Encrypted vault: scrypt key derivation + Fernet (AES) encryption, atomic writes
- Master password is always entered at a hidden prompt, never as an argument

## Requirements

- Python 3.8 or newer
- The [`cryptography`](https://pypi.org/project/cryptography/) package

## Installation

```bash
git clone https://github.com/farukaskaya/AnotherPythonPassGen.git
cd AnotherPythonPassGen
```

Install the dependency:

**Windows / macOS / most Linux distros**

```bash
pip install -r requirements.txt
```

**Arch / Manjaro** (pip is blocked on system-managed Python)

```bash
sudo pacman -S python-cryptography
```

**Debian / Ubuntu** (if pip is blocked)

```bash
sudo apt install python3-cryptography
```

## Usage

### Interactive mode

Run with no arguments:

```bash
python passgen.py
```

You choose **Generate** or **View saved**, then answer the prompts (length, count, character types, exclusions). If you generate a single password, you're offered the option to save it to the vault with a site and username.

### Command-line mode

```bash
python passgen.py [options]
```

| Option | Description |
|---|---|
| `-l`, `--length N` | Password length (default `16`) |
| `-n`, `--count N` | How many passwords to generate (default `1`) |
| `--no-upper` | Exclude uppercase letters |
| `--no-lower` | Exclude lowercase letters |
| `--no-digits` | Exclude digits |
| `--no-symbols` | Exclude symbols |
| `--no-ambiguous` | Exclude look-alike characters (`O 0 o I l 1 \|`) |
| `--exclude CHARS` | Exclude specific characters |
| `--site NAME` | Save the generated password to the vault under this site |
| `--user NAME` | Username to store with it |
| `--view` | Show all saved vault entries |

### Examples

```bash
python passgen.py                                  # 16 chars, everything enabled
python passgen.py -l 24 -n 5                       # five 24-character passwords
python passgen.py --no-symbols --no-ambiguous      # letters and digits, no look-alikes
python passgen.py --exclude "{}[]"                 # avoid specific characters
python passgen.py --site github.com --user alice   # generate and save to the vault
python passgen.py --view                           # list saved entries
```

Tip: when using `--site`, generate one password at a time. With `-n 5` all five would be saved under the same site and username.

## The vault

When you save your first entry, you're asked to create a **master password**. Entries (date, site, username, password) are stored in a single encrypted file:

| OS | Location |
|---|---|
| Linux | `~/.local/share/passgen/vault.bin` |
| Windows | `%APPDATA%\passgen\vault.bin` |

- The key is derived from your master password with scrypt (random salt per vault).
- The data is encrypted and authenticated with Fernet.
- Saves go to a temporary file first and are then swapped in, so a crash mid-save can't destroy the vault.
- **There is no password recovery.** If you forget the master password, the vault is unreadable forever.
- Back up `vault.bin`. Because it's encrypted, a cloud backup is an acceptable risk if your master password is strong.

## Adding it to your application menu

### Linux (`.desktop` entry)

A menu launcher can't pass arguments, and the terminal closes when the script exits. That's why interactive mode exists and ends with "Press Enter to close...".

1. Put the script somewhere permanent, e.g. `~/Applications/passgen.py`.
2. Create `~/.local/share/applications/passgen.desktop` (use your **absolute** path, since `~` and `$HOME` aren't reliably expanded):

   ```ini
   [Desktop Entry]
   Type=Application
   Name=Password Generator
   Comment=Generate secure passwords
   Exec=python3 /home/YOURUSER/Applications/passgen.py
   Icon=dialog-password
   Terminal=true
   Categories=Utility;Security;
   ```

3. Refresh the menu:

   ```bash
   chmod +x ~/.local/share/applications/passgen.desktop
   update-desktop-database ~/.local/share/applications
   ```

If the entry doesn't appear, log out and back in. If it appears but does nothing, run the `Exec` line in a terminal to see the error; a wrong path is the usual cause.

Note: if you copy the script to the install location, you now have two copies. Edit the installed one, or point `Exec` at the copy you edit.

### Windows (Start menu shortcut)

1. Press `Win + R`, run `shell:programs`.
2. Right-click, then **New → Shortcut**.
3. Set the target to:

   ```
   python "C:\Users\YOURNAME\AnotherPythonPassGen\passgen.py"
   ```

   Use `python`, not `pythonw`, otherwise no console window appears.

## Security notes

What this protects against:

- Someone copying `vault.bin` without your master password
- Weak or predictable generation (it uses `secrets`)

What it does **not** protect against:

- **A weak master password.** Anyone with a copy of the vault can guess offline at their leisure. Use a long passphrase (you can generate one with this tool).
- **Malware or a keylogger on your machine.** It sees your master password and the plaintext passwords as you use them.
- **Forgetting the master password.** No recovery exists.
- **Bugs.** This code has not had an independent security review.

On Linux the vault file is created with `600` permissions. Windows ignores Unix permission bits, so on Windows the encryption is your only protection.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing dependency` on start | Install `cryptography` (see [Installation](#installation)) |
| `Wrong master password, or the vault file is damaged` | Check the password; if the file is corrupt, restore from backup |
| `Your exclusions removed every character of an enabled type` | You excluded everything in a type you left enabled. Loosen `--exclude` or disable that type |
| `Length must be at least N` | Length is shorter than the number of enabled character types |
| Menu entry opens and closes instantly | Make sure `Terminal=true` (Linux) or you used `python`, not `pythonw` (Windows) |
| Run the script from a real terminal (Command Prompt, PowerShell, Windows Terminal), because some IDE consoles like IDLE can’t hide the master password while you type it |

## License

MIT. See [LICENSE](LICENSE).
