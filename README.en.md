[中文](README.md) · **English**

# T3 Prompt Patch

Patches the built-in prompts that T3 Code (Nightly) gives Claude and Codex. Afterwards, Claude and Codex working together inside T3 go through [nxbridge](https://github.com/nxbridge/nxbridge) as peer partners instead of through T3's own `delegate_task`. It also relaxes two preview and chart rules.

By default, it patches the prompts and the idle session timeout (patch 7). You can also opt in to disabling T3 Code product usage telemetry. The script backs up the original package so you can restore it.

## Using it with nxbridge

Claude and Codex threads in T3 use your `~/.claude` and `~/.codex` config too, so once nxbridge is installed they load it as well. T3's built-in prompt, however, tells the model to hand work for the other provider to T3's own `delegate_task`; this patch routes it through nxbridge instead.

1. Install nxbridge by following its [installation steps](https://github.com/nxbridge/nxbridge#%E5%AE%89%E8%A3%85) (its README is in Chinese).
2. Run this once in a system terminal:

   ```sh
   nxbridge config set hosts.claude.sdk_user_prompt true
   ```

   T3 passes your input to Claude through the Claude SDK, and by default nxbridge does not treat such input as coming from you. So after you interrupt a running turn in T3 (for example, by sending a new message while Claude is working), nxbridge keeps holding the partner's replies. With this setting on, what you send in T3 counts as your own input and replies arrive normally after an interrupt. The trade-off: input from scripts that run Claude through the SDK (such as `claude -p`) also counts as yours. It is a sensitive nxbridge setting, so run it in a system terminal; running it inside Claude is refused.
3. Run `python3 t3-prompt-patch.py apply`, then quit T3 Code completely and reopen it (see "Usage" below).
4. Open a new Claude thread in T3 and just say "ask Codex to …"; no need to mention nxbridge.

You can apply it without nxbridge too: patches 1 and 2 take effect; patches 3–6 are for nxbridge, see "What changes" below.

## What changes

Seven patches. The first six are in T3's orchestration prompt; the seventh changes one server constant:

| # | Patch | Before | After |
|---|---|---|---|
| 1 | `allow-preview-self-check` | Never use `preview_*` unasked to verify or show your own edit | May use `preview_*` to check your own UI edits when that verifies the result |
| 2 | `charts-on-request` | Answer data with a trend or comparison with a chart | Show a chart when the user asks for one |
| 3 | `nxbridge-no-cli-fallback` | Never switch unasked or fall back to native tools, Workflow or CLIs | Same, plus: the nxbridge partner is no fallback; it is the channel for Claude/Codex work |
| 4 | `nxbridge-peer-partner` | Use `delegate_task` for another provider's model | With nxbridge loaded, the Claude/Codex counterpart is a peer partner, never a `delegate_task` child; follow nxbridge's partner rules (owner by strength, splits, hand-offs, reviews, its own model and effort); `delegate_task` only for other providers or when the user names it |
| 5 | `nxbridge-background` | Background agent: always `delegate_task` | Background agent on your own provider: `delegate_task`; background work for the counterpart goes to the nxbridge partner |
| 6 | `nxbridge-review` | Every review or re-check is a new `delegate_task` | Use nxbridge for an assigned partner review. If unavailable, continue independent work and start a substitute review only on user request. Prefer a fresh native subagent for ordinary same-provider reviews. Follow the existing routing in other cases. |
| 7 | `idle-session-30min` | Close an idle Claude/Codex session process 2 minutes after its turn | Back to 30 minutes |

Compared word by word with T3's original, by kind:

- **2 rules removed**: answer data with a trend or comparison with a chart (patch 2); the ban on using `preview_*` unasked to verify or show your own edit (patch 1, replaced by "may check your own UI edits when that verifies the result"; showing your edit unasked is no longer addressed).
- **3 scopes narrowed**: `delegate_task` for "another provider's model" becomes "models of other providers, not your Claude/Codex counterpart" (patch 4); "background agent: always `delegate_task`" becomes only on your own provider (patch 5); "every review or re-check is a new `delegate_task`" now applies only when existing routing calls for T3 delegation (patch 6).
- **Added**: the nxbridge partner rules and how to message the partner (patch 4), background work and reviews for the counterpart go to the partner (patches 5, 6), the "partner is no fallback" note (patch 3), and native same-provider reviews with user control over partner substitution (patch 6).

Nothing else in T3's prompts changes. The word-level comparison and the full original and patched prompts, with a Chinese paraphrase, are in [docs/prompts-original-vs-patched.zh.md](docs/prompts-original-vs-patched.zh.md).

Patch 7 is not a prompt. Since 0.1.12-nightly.20261123.5138 (upstream [#41174](https://github.com/pingdotgg/t3code/pull/41174)), T3 keeps a natively resumable session (Claude, Codex, OpenCode, Cursor) for 2 minutes after its turn instead of 30, to save memory (about 140 MB per idle Claude process). Once the process is gone, a message from the nxbridge partner waits in the queue until you next type in that thread, so the partner can no longer wake it. This patch sets the constant back to 30 minutes, at the cost of keeping idle processes 28 minutes longer. Earlier versions already use 30 minutes, so `status` shows `patched` there.

Patches 3–6 are written for Claude and Codex with nxbridge: only patch 4 opens with "with nxbridge loaded"; patches 3, 5 and 6 rely on patch 4's "Claude/Codex counterpart" and "nxbridge partner". Other providers such as agy or Pi have no Claude/Codex counterpart, so these lines do not apply to them. Whether a Claude or Codex thread without nxbridge still uses `delegate_task` for its counterpart is untested.

## Usage

Needs Python 3, standard library only (`/usr/bin/python3` on macOS works).

```sh
python3 t3-prompt-patch.py status    # per-patch state: patched / previous / original / NOT FOUND
python3 t3-prompt-patch.py apply     # back up the original and apply (idempotent)
python3 t3-prompt-patch.py restore   # put the backed-up original back
```

After `apply` or `restore`, **quit T3 Code completely and reopen it**. Quitting stops any session running in T3.

An older `nxbridge-review` patch shows as `previous`. Run `apply` to upgrade it and keep the original backup. A T3 Code update replaces the whole package and drops the patch, so run `apply` again and restart T3 after updating. If the new version changed the prompt text, the script lists the patches it cannot find and writes nothing; update `PATCHES` to the new text.

To try it on a copy without touching the installed app:

```sh
cp "/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar" /tmp/app.asar
python3 t3-prompt-patch.py apply --asar /tmp/app.asar
python3 t3-prompt-patch.py status --asar /tmp/app.asar
```

### Disable product usage telemetry

On macOS Nightly, run this command directly:

```sh
(set -o pipefail; curl -fsSL https://raw.githubusercontent.com/MiCat-S/t3-prompt-patch/main/t3-prompt-patch.py | python3 - apply --disable-product-telemetry)
```

If you already downloaded the script, run these commands from its directory:

```sh
python3 t3-prompt-patch.py apply --disable-product-telemetry
python3 t3-prompt-patch.py status --disable-product-telemetry
```

This option applies alongside the existing patches. It stops the local T3 Code server from recording and sending product usage events and skips both account identity lookups used by that telemetry. Direct Tailscale pairing uses the existing connection path. Connection diagnostics sent to Axiom and diagnostics from separate browser or mobile clients are still governed by their own settings or network rules. Verified on macOS Nightly `0.1.12-nightly.20261124.5178`.

Pass the same option again when reapplying after an update. To remove the telemetry patch, run `restore` and then run plain `apply` to reapply the prompt and session patches.

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

On T3 Code 0.1.12-nightly.20261121.5024 with nxbridge 0.1.1-965cfcc58ae0 (all six patches applied, `hosts.claude.sdk_user_prompt` on):

- **Replies after an interrupt**: a T3 Claude thread messaged Codex through nxbridge; while it was busy, the turn was interrupted and a new message sent. Codex's reply arrived normally within the turn after the interrupt instead of being held. Tested in a subtask thread, without a comparison run with the setting off.
- **Subtask threads**: a T3 subtask thread (one spawned by another thread) starts a new Claude process for every turn, and the process exits when the turn ends. A Codex reply that arrives while it is idle is not lost, but it reaches the thread only on its next turn. Regular threads keep one process and are not affected; whether an idle regular thread is woken by a reply was not retested.

On T3 Code 0.1.11-nightly.20261117.4825 with nxbridge 0.1.1-3e3e754f55fa:

- **Claude thread asking Codex**: with only "ask Codex to …" or "have Codex review …" and no mention of nxbridge, Claude used `SendMessage` to `nxbridge:codex`, not `delegate_task`. nxbridge started a background Codex; its reply woke the T3 thread, which relayed the result. The exchange is visible in the T3 thread.
- **Codex thread asking Claude**: Codex also used nxbridge's `send_message`. Starting a background Claude needs a one-time bypass consent in Claude and a trusted working directory (T3's project-less threads live under `~/.t3/scratch/`), so this direction was not fully tested. T3 runs a private `codex app-server` per Codex session, so nxbridge cannot wake an idle Codex thread.

T3 shows the thread's own messages, receipts and its relay of the partner's reply; the background partner's own commands and edits are not shown in T3. To follow the exchange, run `nxbridge watch` in a terminal.

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
