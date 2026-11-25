# 红色警戒：心灵风暴（RedStorm）

《命令与征服：红色警戒 2 - 尤里的复仇》**单人遭遇战玩法**的非官方致敬复刻版。

- 技术栈：Python 3 + pygame-ce + numpy，全部美术与音效由程序实时生成，**不包含任何 EA 原版资源**
- 平台：Windows（已打包为单文件 exe，双击即玩，无需安装 Python）
- 范围：三大阵营（盟军 / 苏军 / 尤里）、完整单位与建筑、资源采集、科技树、超级武器、迷雾、
  单人遭遇战与三档 AI；不含原版战役、过场影片与联机对战

## 快速开始

**方式一（推荐）**：双击 `dist/RedStorm.exe`。

**方式二（源码运行）**：

```powershell
pip install pygame-ce numpy
python main.py
```

进入游戏后：主菜单「开始游戏」→ 选择阵营与难度 → 开始战斗。

## 操作

| 操作 | 功能 |
| --- | --- |
| 左键 / 拖拽 | 选择 / 框选（双击选同类） |
| 右键 | 移动、攻击、采集、占领（按目标智能判定） |
| A + 左键 | 攻击移动 |
| S | 停止 |
| Ctrl + 1~9 / 1~9 | 设置 / 调用编队 |
| H / 空格 | 回基地 / 定位事件 |
| Delete / R | 出售 / 修理选中建筑 |
| ESC | 取消操作 / 暂停 |
| Tab | 切换侧栏标签 |
| M / F11 / F3 | 静音 / 全屏 / FPS |
| 方向键、鼠标贴边、中键拖拽 | 移动视野 |

完整数值与规则见 [docs/游戏规则文档.md](docs/游戏规则文档.md)。

## 目录结构

```
main.py              入口（崩溃时写 crash.log）
game/
  config.py          全局常量与难度参数
  data.py            单位、建筑、武器、弹头倍率等全部数据
  nav.py             群体流场寻路与 A* 寻路
  entities.py        单位 / 建筑 / 弹丸 / 特效
  player.py          资源、生产队列、科技与超级武器
  world.py           地图生成、战斗结算、迷雾、胜负判定
  ai.py              AI 经济、建造、防守与进攻
  render.py          地形、单位、建筑、特效渲染
  ui.py              侧栏、小地图、信息面板
  audio.py           numpy 合成音效
  app.py             菜单 / 设置 / 对局场景与主循环
tools/
  sim_test.py        无头逻辑回归测试（经济、战斗、超级武器、AI 对局）
  render_smoke.py    无头渲染冒烟测试
docs/
  游戏规则文档.md     完整规则与数值
```

## 测试

```powershell
python tools/sim_test.py      # 逻辑回归：数据校验、伤害、核弹、三组 AI 对局
python tools/render_smoke.py  # 渲染冒烟：菜单、对局、选择、标签、覆盖层
```

两项均应输出 `PASSED`。

## 构建 exe

```powershell
pip install pygame-ce numpy pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name RedStorm main.py
```

产物位于 `dist/RedStorm.exe`，单文件、无控制台、无需额外依赖。

## 已知限制

- 无原版战役、真人影片、语音与联机对战
- 敌方 AI 使用与玩家相同的经济规则，仅按难度获得收入 / 生产速度加成
- 地图为随机生成，不含原版官方地图

## 提交规范

提交前先跑通 `tools/sim_test.py` 与 `tools/render_smoke.py`，提交信息格式：

```
<type>(<scope>): <中文简述>
```

- type：`feat` 新功能、`fix` 修复、`perf` 性能、`docs` 文档、`build` 构建、`test` 测试、`chore` 杂项
- scope：`gameplay` / `ai` / `ui` / `render` / `audio` / `data` / `build` 等模块名
- 示例：`fix(ai): 修复矿车被围死后经济断档`、`feat(ui): 新增超级武器瞄准提示`

不要提交 `dist/`、`build/`、`__pycache__/`、`crash.log`（已在 `.gitignore` 中忽略）。

## 版权说明

本项目为学习与致敬用途的非官方作品，《命令与征服：红色警戒 2》相关名称与设定的版权归
Electronic Arts 所有。本项目不包含、不提取、不分发任何原版游戏文件、美术或音频资源。
