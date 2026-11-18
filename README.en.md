[中文](README.md) · **English**

# T3 Prompt Patch

Patches the built-in prompts that T3 Code (Nightly) gives Claude and Codex. Afterwards, Claude and Codex working together inside T3 go through [nxbridge](https://github.com/MiCat-S/nxbridge) as peer partners instead of through T3's own `delegate_task`. It also relaxes two preview and chart rules.

Only prompt text changes; no other T3 code is touched. The original package is backed up first and can be restored at any time.

## What changes

Six patches, all in T3's orchestration prompt:

| # | Patch | Before | After |
|---|---|---|---|
| 1 | `allow-preview-self-check` | Never use `preview_*` unasked to verify or show your own edit | May use `preview_*` to check your own UI edits when that verifies the result |
| 2 | `charts-on-request` | Answer data with a trend or comparison with a chart | Show a chart when the user asks for one |
| 3 | `nxbridge-no-cli-fallback` | Never switch unasked or fall back to native tools, Workflow or CLIs | Same, plus: the nxbridge partner is no fallback; it is the channel for Claude/Codex work |
| 4 | `nxbridge-peer-partner` | Use `delegate_task` for another provider's model | With nxbridge loaded, the Claude/Codex counterpart is a peer partner, never a `delegate_task` child; follow nxbridge's partner rules (owner by strength, splits, hand-offs, reviews, its own model and effort); `delegate_task` only for other providers or when the user names it |
| 5 | `nxbridge-background` | Background agent: always `delegate_task` | Background agent on your own provider: `delegate_task`; background work for the counterpart goes to the nxbridge partner |
| 6 | `nxbridge-review` | Every review or re-check is a new `delegate_task` | Reviews by the counterpart go to the nxbridge partner; all others unchanged |

The full original and patched prompts, with a Chinese paraphrase, are in [docs/prompts-original-vs-patched.zh.md](docs/prompts-original-vs-patched.zh.md).

Patches 3–6 apply only "with nxbridge loaded". Threads without nxbridge, and other providers such as agy or Pi, behave as before.

## Usage

Needs Python 3, standard library only (`/usr/bin/python3` on macOS works).

```sh
python3 t3-prompt-patch.py status    # per-patch state: patched / original / NOT FOUND
python3 t3-prompt-patch.py apply     # back up the original and apply (idempotent)
python3 t3-prompt-patch.py restore   # put the backed-up original back
```

After `apply` or `restore`, **quit T3 Code completely and reopen it**. Quitting stops any session running in T3.

A T3 Code update overwrites the patch; run `apply` again. If the new version changed the prompt text, the script lists the patches it cannot find and writes nothing; update `PATCHES` to the new text.

To try it on a copy without touching the installed app:

```sh
cp "/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar" /tmp/app.asar
python3 t3-prompt-patch.py apply --asar /tmp/app.asar
python3 t3-prompt-patch.py status --asar /tmp/app.asar
```

## How it works

1. Finds the one server bundle in `app.asar` containing `Ordinary coding tasks need no T3 tools.` (currently `apps/server/dist/runtimeLayer-C5lIUtmc.mjs`).
2. Applies each patch as an exact replacement. Each original must occur exactly once; patches already applied are skipped; if any patch matches neither its original nor its replacement, nothing is written.
3. Recomputes that file's size and integrity hash in the asar header (SHA-256, 4 MB blocks); all other files are copied unchanged.
4. Writes to a temp file, verifies every file hash, then atomically replaces the package.
5. On the first `apply` to the installed app, backs up the original to `~/.t3-prompt-patch/backup/<T3 version>/app.asar`, which `restore` uses.

### How the prompt reaches each model

| Model | Injection |
|---|---|
| Claude | Claude Agent SDK `systemPrompt.append` |
| Codex | Codex App Server additional context, as `t3_code_orchestration_01`–`03` |
| ACP providers such as agy | Prepended to the user message in `<t3_code_instructions>` |

All three use the same text, so one replacement covers every provider.

## Tested

On T3 Code 0.1.11-nightly.20261117.4825 with nxbridge 0.1.1-3e3e754f55fa:

- **Claude thread asking Codex**: with only "ask Codex to …" or "have Codex review …" and no mention of nxbridge, Claude used `SendMessage` to `nxbridge:codex`, not `delegate_task`. nxbridge started a background Codex; its reply woke the T3 thread, which relayed the result. The exchange is visible in the T3 thread.
- **Codex thread asking Claude**: Codex also used nxbridge's `send_message`. Starting a background Claude needs a one-time bypass consent in Claude and a trusted working directory (T3's project-less threads live under `~/.t3/scratch/`), so this direction was not fully tested. T3 runs a private `codex app-server` per Codex session, so nxbridge cannot wake an idle Codex thread.

T3 shows the thread's own messages, receipts and its relay of the partner's reply; the background partner's own commands and edits are not shown in T3.

## Notes

- Unofficial; not affiliated with T3 Code. Tested only on the versions above.
- After patching, `codesign --verify` reports `a sealed resource is missing or invalid`, and the `ElectronAsarIntegrity` hash in `Info.plist` no longer matches. The current version still launches. If T3 ever enforces asar integrity, the patched app will not open; run `restore`.
- The app path is hard-coded as `/Applications/T3 Code (Nightly).app`.

## Files

| File | Purpose |
|---|---|
| `t3-prompt-patch.py` | Patch script; the patches are in `PATCHES` at the top |
| `docs/prompts-original-vs-patched.zh.md` | Original vs patched T3 prompts, with a Chinese paraphrase |
