#!/usr/bin/env python3
"""Patch T3 Code's built-in agent prompts inside app.asar.

Usage:
  t3-prompt-patch.py status            # show whether the installed app is patched
  t3-prompt-patch.py apply [--asar P]  # back up original, apply PATCHES (idempotent)
  t3-prompt-patch.py restore           # put the backed-up original app.asar back

Changes take effect after T3 Code is fully quit and reopened.
After a T3 Code update the patch is gone: run `apply` again.
"""
import hashlib, json, os, plistlib, shutil, struct, sys, tempfile

APP = "/Applications/T3 Code (Nightly).app"
HOME = os.path.expanduser("~/.t3-prompt-patch")
# Text below is raw JS template-literal source: a backtick is written as \\` in these Python strings.
PATCHES = [
    {
        "name": "allow-preview-self-check",
        "find": "- Never use \\`preview_*\\` unasked to verify or show your own edit. Use them when",
        "replace": "- You may use \\`preview_*\\` to check your own UI edits when that verifies the result. Also use them when",
    },
    {
        "name": "charts-on-request",
        "find": "- Answer data with a trend or comparison with a chart and show any visual the user asks for here:",
        "replace": "- Show a chart or visual here when the user asks for one:",
    },
    # nxbridge: the Claude/Codex counterpart is a peer partner under nxbridge's own rules, not a T3 delegate.
    {
        "name": "nxbridge-no-cli-fallback",
        "find": "Never switch unasked or fall back to native tools, Workflow or CLIs.",
        "replace": "Never switch unasked or fall back to native tools, Workflow or CLIs (the nxbridge partner is no fallback: it is the channel for Claude/Codex work).",
    },
    {
        "name": "nxbridge-peer-partner",
        "find": "Use \\`delegate_task\\` for another provider's model, user-asked settings,",
        "replace": "With nxbridge loaded, your Claude/Codex counterpart is your nxbridge peer partner, never a \\`delegate_task\\` child or subagent: follow the nxbridge partner rules (owner by strength, agreed splits, hand-offs, reviews, its own model and effort) and message it (Claude: \\`SendMessage\\` to \\`nxbridge:codex\\`, else the nxbridge \\`codex\\` MCP tools; Codex: nxbridge \\`claude.*\\` tools); \\`delegate_task\\` for it only if the user names \\`delegate_task\\`. Use \\`delegate_task\\` for models of other providers (not your counterpart), user-asked settings,",
    },
    {
        "name": "nxbridge-background",
        "find": "Background agent: \\`delegate_task\\`, never a background \\`Agent\\`.",
        "replace": "Background agent on your provider: \\`delegate_task\\`, never a background \\`Agent\\`; background work for your counterpart goes to the nxbridge partner.",
    },
    {
        "name": "nxbridge-review",
        "find": "- Every new delegate review or re-check is a new \\`delegate_task\\`",
        "previous": "- A review or re-check by your Claude/Codex counterpart: message the nxbridge partner. Every other new delegate review or re-check is a new \\`delegate_task\\`",
        "replace": "- For a review or re-check assigned to your nxbridge partner, message that partner. If it is unavailable, report the blocker and continue independent work. Only start a substitute review if the user asks. For other reviews, follow the subagent routing above. Prefer a fresh native subagent for an ordinary same-provider review. When that routing requires T3 delegation, start a new \\`delegate_task\\`",
    },
]
MARKER = "Ordinary coding tasks need no T3 tools."
BLOCK = 4 * 1024 * 1024


def read_asar(path):
    with open(path, "rb") as f:
        data = f.read()
    (four,) = struct.unpack_from("<I", data, 0)
    (pickle_size,) = struct.unpack_from("<I", data, 4)
    (str_len,) = struct.unpack_from("<I", data, 12)
    assert four == 4, "not an asar file"
    header = json.loads(data[16 : 16 + str_len].decode("utf-8"))
    return data, header, 8 + pickle_size


def write_asar(path, header, chunks):
    s = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    pad = (4 - len(s) % 4) % 4
    payload = struct.pack("<I", len(s)) + s + b"\0" * pad
    pickle = struct.pack("<I", len(payload)) + payload
    with open(path, "wb") as f:
        f.write(struct.pack("<II", 4, len(pickle)))
        f.write(pickle)
        for c in chunks:
            f.write(c)


def files(node, prefix=""):
    for name, child in node.get("files", {}).items():
        p = f"{prefix}/{name}" if prefix else name
        if "files" in child:
            yield from files(child, p)
        elif "offset" in child and not child.get("unpacked"):
            yield p, child


def integrity(buf):
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(buf).hexdigest(),
        "blockSize": BLOCK,
        "blocks": [hashlib.sha256(buf[i : i + BLOCK]).hexdigest() for i in range(0, max(len(buf), 1), BLOCK)],
    }


def content(data, base, entry):
    off = base + int(entry["offset"])
    return data[off : off + entry["size"]]


def find_target(data, base, header):
    hits = [
        (p, e)
        for p, e in files(header)
        if p.startswith("apps/server/dist/") and p.endswith(".mjs") and MARKER.encode() in content(data, base, e)
    ]
    if len(hits) != 1:
        sys.exit(f"Expected one server bundle with the prompts, found {len(hits)}. T3 Code changed; update this script.")
    return hits[0]


def match_patch(text, patch):
    forms = [("original", patch["find"]), ("patched", patch["replace"])]
    if "previous" in patch:
        forms.append(("previous", patch["previous"]))
    matches = [(state, value) for state, value in forms if value in text]
    if len(matches) == 1 and text.count(matches[0][1]) == 1:
        return matches[0]
    return "NOT FOUND", None


def patch_text(text):
    done, already, missing = [], [], []
    for p in PATCHES:
        state, value = match_patch(text, p)
        if state in ("original", "previous"):
            text = text.replace(value, p["replace"])
            done.append(p["name"])
        elif state == "patched":
            already.append(p["name"])
        else:
            missing.append(p["name"])
    return text, done, already, missing


def version():
    with open(os.path.join(APP, "Contents/Info.plist"), "rb") as f:
        return plistlib.load(f)["CFBundleShortVersionString"]


def backup_path():
    return os.path.join(HOME, "backup", version(), "app.asar")


def cmd_status(asar):
    data, header, base = read_asar(asar)
    path, entry = find_target(data, base, header)
    text = content(data, base, entry).decode("utf-8")
    print(f"T3 Code {version()}  bundle: {path}")
    for p in PATCHES:
        state, _ = match_patch(text, p)
        print(f"  {p['name']}: {state}")
    print(f"  backup: {backup_path() if os.path.exists(backup_path()) else 'none'}")


def cmd_apply(asar, in_place_app):
    data, header, base = read_asar(asar)
    path, entry = find_target(data, base, header)
    new_text, done, already, missing = patch_text(content(data, base, entry).decode("utf-8"))
    if missing:
        sys.exit(f"Patch text not found (T3 Code changed these prompts): {', '.join(missing)}. Nothing written.")
    if not done:
        print(f"Already patched: {', '.join(already)}. Nothing to do.")
        return
    if in_place_app:
        bp = backup_path()
        if not os.path.exists(bp):
            os.makedirs(os.path.dirname(bp), exist_ok=True)
            shutil.copy2(asar, bp)
            print(f"Backed up original to {bp}")
    new_buf = new_text.encode("utf-8")
    entries = sorted(files(header), key=lambda pe: int(pe[1]["offset"]))
    chunks, offset = [], 0
    for p, e in entries:
        buf = new_buf if p == path else content(data, base, e)
        if p == path:
            e["size"] = len(buf)
            e["integrity"] = integrity(buf)
        e["offset"] = str(offset)
        chunks.append(buf)
        offset += len(buf)
    tmp = tempfile.NamedTemporaryFile(dir=os.path.dirname(asar), prefix=".app.asar.", delete=False).name
    write_asar(tmp, header, chunks)
    verify(tmp, path, new_buf)
    os.chmod(tmp, os.stat(asar).st_mode)
    os.replace(tmp, asar)
    print(f"Applied: {', '.join(done)}" + (f" (already: {', '.join(already)})" if already else ""))
    print("Quit T3 Code completely and reopen it for the change to take effect.")


def verify(path, target, expected):
    data, header, base = read_asar(path)
    for p, e in files(header):
        buf = content(data, base, e)
        if p == target and buf != expected:
            sys.exit("Verification failed: patched file mismatch.")
        if "integrity" in e and hashlib.sha256(buf).hexdigest() != e["integrity"]["hash"]:
            sys.exit(f"Verification failed: {p} hash mismatch.")


def cmd_restore(asar):
    bp = backup_path()
    if not os.path.exists(bp):
        sys.exit(f"No backup for T3 Code {version()} at {bp}.")
    shutil.copy2(bp, asar + ".restore")
    os.replace(asar + ".restore", asar)
    print("Restored original app.asar. Quit and reopen T3 Code.")


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    custom = args[args.index("--asar") + 1] if "--asar" in args else None
    asar = custom or os.path.join(APP, "Contents/Resources/app.asar")
    if cmd == "status":
        cmd_status(asar)
    elif cmd == "apply":
        cmd_apply(asar, in_place_app=custom is None)
    elif cmd == "restore":
        cmd_restore(asar)
    else:
        sys.exit(__doc__)
