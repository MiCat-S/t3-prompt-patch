**中文** · [English](README.en.md)

# T3 Prompt Patch

修改 T3 Code（Nightly）内置给 Claude 和 Codex 的提示词。改完后，在 T3 里 Claude 和 Codex 之间的协作改走 [nxbridge](https://github.com/MiCat-S/nxbridge)，两边是平级搭档，不再走 T3 自己的 `delegate_task`。顺带放宽两处预览和图表规则。

只改提示词文本，不改 T3 的其他代码。改之前会备份原包，随时可以恢复。

## 和 nxbridge 一起用

这个补丁要配合 [nxbridge](https://github.com/MiCat-S/nxbridge) 使用：先照 nxbridge 的说明装好它，再打这个补丁。T3 里哪个方向能用、界面上能看到什么、还要注意什么，见 nxbridge README 的“[和 T3 Code 一起用](https://github.com/MiCat-S/nxbridge#%E5%92%8C-t3-code-%E4%B8%80%E8%B5%B7%E7%94%A8)”。

没装 nxbridge 也可以打：补丁 1、2 照常生效；补丁 3~6 是给 nxbridge 用的，见下文“改了什么”。

## 改了什么

一共 6 条补丁，都在 T3 的协作提示词里：

| # | 补丁名 | 原来 | 现在 |
|---|---|---|---|
| 1 | `allow-preview-self-check` | 没人要求时，不准用 `preview_*` 验证或展示自己的改动 | 为了验证结果，可以用 `preview_*` 检查自己改的界面 |
| 2 | `charts-on-request` | 有趋势或对比的数据，主动用图表回答 | 用户要求时才展示图表 |
| 3 | `nxbridge-no-cli-fallback` | 不准擅自换，不准退回原生工具、Workflow 或命令行 | 同原来，并写明 nxbridge 搭档不算退回，它就是 Claude/Codex 协作的通道 |
| 4 | `nxbridge-peer-partner` | 要用另一家的模型，走 `delegate_task` | 装了 nxbridge 时，Claude/Codex 对方是平级搭档、不是 `delegate_task` 子任务，按 nxbridge 的规则协作（按擅长分工、交接、复查，对方自己定模型和强度）；`delegate_task` 只用于其他家，或你点名时 |
| 5 | `nxbridge-background` | 后台代理一律走 `delegate_task` | 自己这一家的后台代理走 `delegate_task`；给对方的后台工作交给 nxbridge 搭档 |
| 6 | `nxbridge-review` | 每次审查或复查都新开一个 `delegate_task` | 要对方审查或复查的，发给 nxbridge 搭档；其余照旧 |

和 T3 原版逐词比对，按类型分：

- **删掉 2 条规则**：有趋势或对比的数据要主动用图表回答（补丁 2）；没人要求时不准用 `preview_*` 验证或展示自己改动的禁令（补丁 1，换成了“为了验证结果，可以检查自己改的界面”；没人要求时主动展示给用户看，现版没有写）。
- **缩小了 3 处适用范围**，原文保留：`delegate_task` 用于“另一家的模型”改成“其他家的模型，不含你的 Claude/Codex 对方”（补丁 4）；后台代理一律走 `delegate_task` 改成只限自己这一家（补丁 5）；每次审查都新开 `delegate_task` 改成对方做的审查除外（补丁 6）。
- **新加**：nxbridge 搭档规则和发消息的方式（补丁 4），对方的后台工作和审查交给搭档（补丁 5、6），“搭档不算退回”的括注（补丁 3）。

除此之外，T3 的提示词一字未动。逐词对照、完整的原版和现版原文及中文转述见 [docs/prompts-original-vs-patched.zh.md](docs/prompts-original-vs-patched.zh.md)。

补丁 3~6 是为装了 nxbridge 的 Claude 和 Codex 写的：只有第 4 条开头写明“装了 nxbridge 时”，第 3、5、6 条靠第 4 条里“Claude/Codex 对方”“nxbridge 搭档”的定义限定范围。agy、Pi 等其他提供方没有 Claude/Codex 对方，这几句对它们不适用。没装 nxbridge 的 Claude/Codex 线程能否照旧用 `delegate_task` 找对方，没有实测。

## 使用

需要 Python 3，只用标准库，不用装依赖（macOS 上的 `/usr/bin/python3` 即可）。

```sh
python3 t3-prompt-patch.py status    # 查看每条补丁的状态：patched / original / NOT FOUND
python3 t3-prompt-patch.py apply     # 备份原包并打上补丁（可重复运行）
python3 t3-prompt-patch.py restore   # 恢复备份的原包
```

`apply` 和 `restore` 之后，要**完全退出 T3 Code 再重新打开**才生效。退出会中断 T3 里正在运行的会话。

T3 Code 更新后补丁会被覆盖，重新运行一次 `apply` 即可。如果新版本改了相关的提示词原文，脚本会列出找不到的补丁，并且不写入任何东西，这时需要按新原文更新脚本里的 `PATCHES`。

只想在副本上试，不动已安装的 T3：

```sh
cp "/Applications/T3 Code (Nightly).app/Contents/Resources/app.asar" /tmp/app.asar
python3 t3-prompt-patch.py apply --asar /tmp/app.asar
python3 t3-prompt-patch.py status --asar /tmp/app.asar
```

## 工作原理

1. 在 `app.asar` 里找到包含 `Ordinary coding tasks need no T3 tools.` 的服务端代码文件（文件名随版本变化，0.1.11-nightly.20261118.4864 上是 `apps/server/dist/runtimeLayer-DiBNK4ph.mjs`），必须正好找到一个。
2. 逐条精确替换。每条补丁的原文必须在文件里正好出现一次；已经打过的跳过；任何一条既找不到原文、也找不到替换后的文字，就整体放弃，不写入。
3. 重新计算 asar 头里这个文件的大小和完整性哈希（SHA-256，4 MB 分块），其他文件原样保留。
4. 先写到临时文件，校验所有文件的哈希都对，再原子替换原包。
5. 第一次 `apply` 已安装的 T3 时，把原包备份到 `~/.t3-prompt-patch/backup/<T3 版本>/app.asar`。`restore` 用的就是这份备份。

### 提示词怎么到达模型

| 模型 | 注入方式 |
|---|---|
| Claude | Claude Agent SDK 的 `systemPrompt.append`，追加在系统提示词末尾 |
| Codex | Codex App Server 的附加上下文，分成 `t3_code_orchestration_01`~`03` 三条 |
| agy 等 ACP 提供方 | 拼在用户消息前面的 `<t3_code_instructions>` 里 |

三者用的是同一份提示词文本，所以一次替换对所有提供方都生效。

## 实测

在 T3 Code 0.1.11-nightly.20261117.4825、nxbridge 0.1.1-3e3e754f55fa 上测过：

- **Claude 线程找 Codex**：只说“请 Codex 回答……”或“请让 Codex 复查……”，没有提 nxbridge。Claude 用 `SendMessage` 发给 `nxbridge:codex`，没有调用 `delegate_task`。nxbridge 自动配了后台 Codex；Codex 回信后，T3 线程被自动叫醒并转述结果。整个往来在 T3 线程里可见。
- **Codex 线程找 Claude**：Codex 也走了 nxbridge 的 `send_message`。但 nxbridge 要启动后台 Claude，需要先在 Claude 里做一次免审批确认，并信任工作目录（T3 无项目线程的目录在 `~/.t3/scratch/` 下）。这个方向没有测完。另外，T3 给每个 Codex 会话单独起私有的 `codex app-server`，nxbridge 无法在 Codex 线程空闲时叫醒它。

T3 里能看到的是本线程发出的消息、回执和对方回信后的转述；后台搭档自己执行的命令和改动不在 T3 里显示。

T3 Code 0.1.11-nightly.20261118.4864：提示词原文和 4825 逐字相同；在 `app.asar` 副本上 `apply`、`status` 都通过，打补丁前后只有这 6 处不同。上面的行为测试没有在这个版本上重做。

## 注意

- 这是非官方补丁，和 T3 Code 官方无关。只在上面列的版本上测过。
- 修改后，`codesign --verify` 会报告 app 内的资源封印无效（`a sealed resource is missing or invalid`），`Info.plist` 里 `ElectronAsarIntegrity` 记录的哈希也不再匹配。当前版本在本机仍能正常启动。如果以后 T3 开启了 asar 完整性强制校验，打过补丁的版本会打不开，用 `restore` 恢复即可。
- 脚本里写死的 app 路径是 `/Applications/T3 Code (Nightly).app`。

## 文件

| 文件 | 说明 |
|---|---|
| `t3-prompt-patch.py` | 补丁脚本，补丁内容在文件开头的 `PATCHES` 里 |
| `docs/prompts-original-vs-patched.zh.md` | T3 提示词原版与现版对照，附中文转述 |
| `LICENSE` | MIT 许可证 |

## 许可证

[MIT](LICENSE)。MIT 只适用于本仓库自己写的脚本和文档；文档和脚本里引用的 T3 Code 提示词原文，版权归 T3 Code 的作者。
