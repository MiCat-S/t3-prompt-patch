[中文](README.md) · **English**

# T3 Prompt Patch

Patches the built-in prompts that T3 Code (Nightly) gives Claude and Codex. Afterwards, Claude and Codex working together inside T3 go through [nxbridge](https://github.com/MiCat-S/nxbridge) as peer partners instead of through T3's own `delegate_task`. It also relaxes two preview and chart rules.

Only prompt text changes; no other T3 code is touched. The original package is backed up first and can be restored at any time.

## Using it with nxbridge

This patch is meant to be used with [nxbridge](https://github.com/MiCat-S/nxbridge): install nxbridge first by following its instructions, then apply this patch. For which directions work in T3, what T3 shows and what to watch out for, see [Using it with T3 Code](https://github.com/MiCat-S/nxbridge/blob/main/README.en.md#using-it-with-t3-code) in the nxbridge README.

You can apply it without nxbridge too: patches 1 and 2 take effect; patches 3–6 are for nxbridge, see "What changes" below.

## What changes

Six patches, all in T3's orchestration prompt:

| # | Patch | Before | After |
|---|---|---|---|
| 1 | `allow-preview-self-check` | Never use `preview_*` unasked to verify or show your own edit | May use `preview_*` to check your own UI edits when that verifies the result |
| 2 | `charts-on-request` | Answer data with a trend or comparison with a chart | Show a chart when the user asks for one |
| 3 | `nxbridge-no-cli-fallback` | Never switch unasked or fall back to native tools, Workflow or CLIs | Same, plus: the nxbridge partner is no fallback; it is the channel for Claude/Codex work |
| 4 | `nxbridge-peer-partner` | Use `delegate_task` for another provider's model | With nxbridge loaded, the Claude/Codex counterpart is a peer partner, never a `delegate_task` child; follow nxbridge's partner rules (owner by strength, splits, hand-offs, reviews, its own model and effort); `delegate_task` only for other providers or when the user names it |
| 5 | `nxbridge-background` | Background agent: always `delegate_task` | Background agent on your own provider: `delegate_task`; background work for the counterpart goes to the nxbridge partner |
| 6 | `nxbridge-review` | Every review or re-check is a new `delegate_task` | Use nxbridge for an assigned partner review. If unavailable, continue independent work and start a substitute review only on user request. Prefer a fresh native subagent for ordinary same-provider reviews. Follow the existing routing in other cases. |

Compared word by word with T3's original, by kind:

- **2 rules removed**: answer data with a trend or comparison with a chart (patch 2); the ban on using `preview_*` unasked to verify or show your own edit (patch 1, replaced by "may check your own UI edits when that verifies the result"; showing your edit unasked is no longer addressed).
- **3 scopes narrowed**: `delegate_task` for "another provider's model" becomes "models of other providers, not your Claude/Codex counterpart" (patch 4); "background agent: always `delegate_task`" becomes only on your own provider (patch 5); "every review or re-check is a new `delegate_task`" now applies only when existing routing calls for T3 delegation (patch 6).
- **Added**: the nxbridge partner rules and how to message the partner (patch 4), background work and reviews for the counterpart go to the partner (patches 5, 6), the "partner is no fallback" note (patch 3), and native same-provider reviews with user control over partner substitution (patch 6).

Nothing else in T3's prompts changes. The word-level comparison and the full original and patched prompts, with a Chinese paraphrase, are in [docs/prompts-original-vs-patched.zh.md](docs/prompts-original-vs-patched.zh.md).

Patches 3–6 are written for Claude and Codex with nxbridge: only patch 4 opens with "with nxbridge loaded"; patches 3, 5 and 6 rely on patch 4's "Claude/Codex counterpart" and "nxbridge partner". Other providers such as agy or Pi have no Claude/Codex counterpart, so these lines do not apply to them. Whether a Claude or Codex thread without nxbridge still uses `delegate_task` for its counterpart is untested.

## Usage

Needs Python 3, standard library only (`/usr/bin/python3` on macOS works).

```sh
python3 t3-prompt-patch.py status    # per-patch state: patched / previous / original / NOT FOUND
python3 t3-prompt-patch.py apply     # back up the original and apply (idempotent)
python3 t3-prompt-patch.py restore   # put the backed-up original back
```

After `apply` or `restore`, **quit T3 Code completely and reopen it**. Quitting stops any session running in T3.

An older `nxbridge-review` patch shows as `previous`. Run `apply` to upgrade it and keep the original backup. Run `apply` again after a T3 Code update. If the new version changed the prompt text, the script lists the patches it cannot find and writes nothing; update `PATCHES` to the new text.

To try it on a copy without touching the installed app:

```sh
cp "/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar" /tmp/app.asar
python3 t3-prompt-patch.py apply --asar /tmp/app.asar
python3 t3-prompt-patch.py status --asar /tmp/app.asar
```

## How it works

1. Finds the one server bundle in `app.asar` containing `Ordinary coding tasks need no T3 tools.` (the file name changes between versions; on 0.1.11-nightly.20261118.4864 it is `apps/server/dist/runtimeLayer-DiBNK4ph.mjs`).
2. Applies each patch as an exact replacement. Each patch must have a single match across its original, current and known previous forms. Original and previous forms are updated. Current forms are skipped. An ambiguous or absent match stops the update.
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

T3 Code 0.1.11-nightly.20261118.4864: the prompt text is identical to 4825; `apply` and `status` pass on a copy of `app.asar`, and only these six spots differ after patching. The behavior tests above were not repeated on this version.

## Notes

- Unofficial; not affiliated with T3 Code. Tested only on the versions above.
- After patching, `codesign --verify` reports `a sealed resource is missing or invalid`, and the `ElectronAsarIntegrity` hash in `Info.plist` no longer matches. The current version still launches. If T3 ever enforces asar integrity, the patched app will not open; run `restore`.
- The app path is hard-coded as `/Applications/T3 Code (Nightly).app`.

## Files

| File | Purpose |
|---|---|
| `t3-prompt-patch.py` | Patch script; the patches are in `PATCHES` at the top |
| `docs/prompts-original-vs-patched.zh.md` | Original vs patched T3 prompts, with a Chinese paraphrase |
| `LICENSE` | MIT license |

## License

[MIT](LICENSE). It covers only this repository's own script and documentation; the T3 Code prompt text quoted in them belongs to the T3 Code authors.
