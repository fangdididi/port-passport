# 《砖块小镇》C + SDL 桌面游戏 → 浏览器（WebAssembly）移植日志

## 身份表（节选）
- 源：v1.2 @ 7c09，C11 + SDL2，Linux x86_64 与 Windows x64 发行，使用桌面 OpenGL 2.1 固定管线。
- 目标：`web-chromium`（Chrome 130，桌面）、`web-firefox`（Firefox 131，桌面）。
- 任务类型：实施。用户只授权在本机浏览器测试，不发布。
- 黄金场景（改动前在 Linux 上录制，固定 1280×720、固定随机种子 42）：
  `title`（标题画面截图）、`level1`（第 1 关开局 3 秒截图 + 分数）、`save`（存档 → 退出 → 读档后的关卡与分数）。

## 隐患表
| 层 | 隐患 | 位置 | 修法 | 成本 | 阻塞哪一级 |
| --- | --- | --- | --- | --- | --- |
| 时间与线程 | `while(running)` 主循环从不让出 | `main.c:88` | 改为每帧回调 | M | first-light |
| 媒体 | `glBegin/glEnd` 固定管线，WebGL 不支持 | `render.c` 全文件 | 换成顶点缓冲 + 最小着色器 | L | first-light |
| 文件系统 | 同步 `fopen("save.dat")` | `save.c:14` | 映射到浏览器持久存储，退出前显式刷新 | M | round-trip |
| 时间与线程 | 音频线程 | `audio.c:40` | 先走单线程混音回调；多线程需跨源隔离响应头 | M | endures |
| 输入 | 键盘轮询依赖窗口焦点 | `input.c:22` | 处理失焦时释放全部按键 | S | interacts |

路线：保留游戏逻辑与数据格式，仅替换平台层（循环、渲染、存储、音频、输入）。

## 第 3 轮 — web-chromium — 构建 7c09-w3
- 故障层：呈现。页面加载、日志显示进入 `main`，但画布全黑。
- 假设（可证伪）：主循环从不让出，浏览器从未有机会绘制。若加帧计数器后计数 > 0，则假设被推翻。
- 证据：帧计数器停在 0，标签页 CPU 100%。假设成立。
- 已排除的反例：不是着色器编译失败——着色器日志为空且无报错。
- 修改：注册每帧回调，删除阻塞循环；关闭诊断后在新标签页复测。
- 护照：Chromium 盖章 launches、first-light（标题画面与黄金截图肉眼一致，证据 `port/evidence/w3/title.png`）。

## 第 4 轮 — web-chromium — 构建 7c09-w4
- 故障层：行为。读档后分数归零。
- 假设：写入只在内存文件系统，刷新页面前未落到持久存储。若在退出钩子里显式同步后分数保留，则假设成立。
- 结果：成立。护照：interacts（方向键移动角色，前后截图位置不同）、round-trip（关闭标签页 → 新标签页读档 → 关卡 1、分数 340 与存档前一致）。
- 未验证：parity（level1 截图与黄金图有 2px 偏移，待查 HiDPI 缩放）；Firefox 目标仍停在 builds——尚未在 Firefox 中运行 w4。
- 下一阻塞：HiDPI 下画布尺寸；检查方法：在 devicePixelRatio = 1 与 2 下各截一张，与黄金图逐像素比较。

## 诚实结论
- web-chromium（构建 7c09-w4）已到达 round-trip；尚不能说明其行为与原版一致（parity 未过）。
- web-firefox（构建 7c09-w4）仅有 builds；不能借用 Chromium 的结果。
