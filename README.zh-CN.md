# port-passport（移植护照）

[English](./README.md) · **简体中文**

> 把能跑的软件搬到新平台——并且永远不宣称超出你亲眼看到它在那里跑出来的东西。

**port-passport** 是一个面向*移植*的 agent skill：把已经能用的软件，搬到新的地方也能用——另一种操作系统、
另一种 CPU 架构、手机或平板、通过 WebAssembly 进入浏览器，或者带有破坏性变更的运行时/框架新版本。把你的
编码 agent 指向一个仓库和一个目标，它会钉死"今天到底在跑什么"，录下原版的黄金行为，逐层绘制隐患图，
先把一条最细的端到端路径打通到"首次出画"，然后每轮只拆除一个真实阻塞。

每个目标都有一本**护照**：八级证据阶梯——
`builds → launches → first-light → interacts → round-trip → parity → endures → ships`——每一级只能凭
*当前*构建、*指定*设备上的书面证据盖章。新构建会让旧章过期；Mac 的结果永远不算 iPad 的。agent 的状态
报告从护照生成，所以"能编译"永远不会悄悄变成"能用"。

## 有何不同

- **证据阶梯，而不是百分比。** 每一级都写明它证明了什么、**没有**证明什么。状态句会是这样的：
  "macos-arm64（构建 7c09-r4）已到达 first-light……尚不能说明它会响应输入。"
- **先录黄金行为。** 在第一次修改**之前**记录原版的表现，让"行为一样"变成逐文件的一致性比对，而不是一种看法。
- **按层定位排错。** 每个故障都先钉到某一层（身份 → 构建 → 装载 → 平台层 → API → 渲染/IO → 呈现 → 行为），
  再用一个可证伪的假设去攻。
- **拒绝遮掩。**"返回成功"的空桩、跳过的绘制、硬编码数值都算缺陷。
- **适用于任何移植**——命令行、桌面应用、游戏、移动应用、服务——以及任何技术栈。

## 功能

- **身份表**：源与每个目标的版本、架构、签名、分发渠道，用真实制品核实，而不是看文件名。
- **黄金场景**：在源平台上录制，并注明不确定因素及其处理方式。
- **隐患图**：覆盖十层——构建、CPU/ABI、系统 API、文件系统、文本与区域设置、进程、时间与线程、媒体与输入、
  网络与存储、打包——外加一条"由省到贵"的路线阶梯。
- **`scripts/portscan.py`**：零依赖的快速隐患初筛（约 35 条规则，按层分组，可按目标过滤：linux、macos、
  windows、ios、android、wasm、arm64；输出 Markdown 或 JSON）。
- **`scripts/passport.py`**：护照本体。没有证据、下方有空级、或尚未记录构建时拒绝盖章；新构建会把旧章标为
  过期；`revoke` 记录回归；`claim` 生成一句诚实的状态；`parity` 比较黄金输出与目标输出（可选忽略换行符/
  行尾空白，有差异则非零退出）。
- **移植日志与交接模板**：每一轮都记录假设、证据、反例和下一项检查。
- **完整示例**：Python 命令行工具迁到 Windows（真实扫描结果 + 护照），以及 C/SDL 游戏搬进浏览器（中文日志）。
- **完整的中英文版本** skill 与文档。

## 安装

```bash
git clone https://github.com/fangdididi/port-passport.git
```

### Claude Code
把 skill 复制到 skills 目录（项目级 `.claude/skills/` 或用户级 `~/.claude/skills/`）：

```bash
mkdir -p .claude/skills/port-passport
cp -r port-passport/* .claude/skills/port-passport/
```

Claude Code 会根据 frontmatter 自动发现它；让它"移植""迁移""让这个能在……上跑"，或直接按名字调用。

### Codex
把文件夹放到 Codex 加载 skills 的位置（例如它读取的 `skills/` 目录，如 `~/.codex/skills/port-passport`），
或在 `AGENTS.md` 中引用 `SKILL.md`。

### Cursor
把文件夹放进仓库（如 `.cursor/skills/port-passport/`）并引用 `SKILL.md`，或把其中的指导粘贴到
`.cursor/rules/` 下的规则里。然后让 agent 执行移植或审计移植进度。

### 其他 agent
`SKILL.md` 是带 YAML frontmatter 的普通 Markdown。交给任何能遵循指令的 agent（Gemini CLI、OpenCode、
Copilot、Windsurf、Aider……），用 Python 3.8+ 运行辅助脚本即可。

## 使用方法

告诉 agent 今天在哪跑、接下来要去哪跑、允许它做到哪一步：

```
用 port-passport 把这个仓库移植到 Apple Silicon 的 macOS 和 Windows x64。
现在它跑在 Ubuntu x86_64 上。可以在本地构建和运行；不要签名或发布。
```

agent 会填写 `port/identity.md`，把黄金场景录到 `port/golden/`，扫描并绘制隐患图，选定路线，切出平台接缝，
打通细切片，并在 `port/log.md` 中记录每一轮，同时给 `port/passport.json` 盖章。

### 辅助脚本

```bash
# 针对目标做隐患初筛
python3 scripts/portscan.py path/to/repo --target windows > port/scan.md
python3 scripts/portscan.py path/to/repo --target wasm --json

# 护照
python3 scripts/passport.py init --project myapp --source "Ubuntu 24.04 x86_64, Python 3.11"
python3 scripts/passport.py target windows-x64 --desc "Windows 11, Python 3.11"
python3 scripts/passport.py build windows-x64 a1f3-r1
python3 scripts/passport.py stamp windows-x64 builds --evidence "pip install . 退出码 0"
python3 scripts/passport.py claim windows-x64
python3 scripts/passport.py parity port/golden port/out/windows-x64 --eol
python3 scripts/passport.py show --md > port/PASSPORT.md

# 自测
python3 tests/test_scripts.py
```

## 示例

**之前：**"Windows 版基本搞定了——能编译，帮助文本也能显示。"

**之后（自动生成的护照）：**

```
| 目标        | 构建    | builds | launches | first-light | interacts | round-trip | parity | endures | ships |
| windows-x64 | a1f3-r3 | ✅     | ✅       | ✅          | ✅        | ✅         | ✅     | —       | —     |
| macos-arm64 | a1f3-r3 | ✅     | —        | —           | —         | —          | —      | —       | —     |

- windows-x64（构建 a1f3-r3）已在 Win11 虚拟机上到达 parity：3 个黄金场景一致、0 个差异。
  尚不能说明它能长时间或高负载运行。
- macos-arm64（构建 a1f3-r3）仅到达 builds：在 M2 上 pip install 成功。尚不能说明它能启动或可用。
```

完整的扫描、日志和护照见 [`examples/cli-to-windows/`](examples/cli-to-windows/)，浏览器移植见
[`examples/game-to-web/`](examples/game-to-web/)。

## 文件结构

```
port-passport/
├── SKILL.md                         # skill（英文）
├── SKILL.zh-CN.md                   # skill（中文）
├── README.md                        # README（英文）
├── README.zh-CN.md                  # 本文件
├── LICENSE                          # MIT
├── references/
│   ├── hazard-map.md                # 十层隐患清单 + 路线阶梯
│   └── port-log-template.md         # 身份表、单轮记录、交接模板
├── scripts/
│   ├── portscan.py                  # 可移植性隐患初筛
│   └── passport.py                  # 证据阶梯护照 + 一致性比对
├── tests/
│   └── test_scripts.py              # 两个脚本的自测
└── examples/
    ├── cli-to-windows/              # Python CLI → Windows/macOS（扫描、日志、护照）
    └── game-to-web/                 # C + SDL 游戏 → WebAssembly（中文日志）
```

## 许可证

MIT —— 见 [LICENSE](./LICENSE)。
