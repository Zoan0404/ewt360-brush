# 🚀 EWT360 傻瓜式刷课工具 — 完整使用教程

> 版本：v3.0（2026-10-01）
> **推荐文件**：`ewt_brush_optimized.py`（单文件完整版，无需其他文件）
> 一句话：**运行后按提示回答几个问题，自动完成登录、识别课时、刷课、监控、验证。**

---

## 目录
1. [这是什么？能干什么？](#1-这是什么能干什么)
2. [文件说明（为什么 easy 这么小）](#2-文件说明为什么-easy-这么小)
3. [傻瓜式用法（电脑 / 安卓 / iPhone）](#3-傻瓜式用法电脑--手机--iphone)
   - 3.1 [电脑端（Windows / macOS / Linux）](#31-️-电脑端windows--macos--linux)
   - 3.2 [安卓手机（Termux / Pydroid3）](#32--手机端termux-推荐--pydroid3-备选)
   - 3.3 [iPhone / iPad（iOS）](#33--iphone--ipadios)
   - 3.4 [如何查看进度（重点）](#34--如何查看进度重点)
4. [概念详解：刷课到底在刷什么](#4-概念详解刷课到底在刷什么)
5. [参数详解：每个数字是什么意思](#5-参数详解每个数字是什么意思)
6. [效率指标：刷课时长 ÷ 视频总时长](#6-效率指标刷课时长--视频总时长)
7. [推荐配置速查（照着填就行）](#7-推荐配置速查照着填就行)
8. [多实例并行原理（为什么要开多个）](#8-多实例并行原理为什么要开多个)
9. [脚本自己会处理的事（不用你操心）](#9-脚本自己会处理的事不用你操心)
10. [常见问题 FAQ](#10-常见问题-faq)
11. [安全提示](#11-安全提示)
12. [强制重刷所有课时（高级）](#12-强制重刷所有课时高级)

---

## 1. 这是什么？能干什么？

EWT360（升学 e网通）是一个网课平台，老师会布置**作业**，作业里有大量**视频课时**，每个课时要求看完（比如 20 分钟的视频必须播放满 20 分钟才算完成）。

本工具的作用：**自动代替你"看"这些视频**，把几十个小时的视频课压缩到几分钟刷完，进度 100% 完成。

| 功能 | 说明 |
|---|---|
| 自动登录 | 输入账号密码即可，不用手动抓 token |
| 自动识别任务 | 扫描出所有未完成的课时（含时长） |
| 极速刷课 | 竞态爆发技术，比正常观看快 ~5 倍以上 |
| 自动处理风控 | WAF 拦截自动冷却重试 |
| 自动续期 | token 失效自动重新登录，不中断 |
| 看课检测兜底 | 弹题绕过 / 看课检测 / 重刷修复，三重保障 |
| 多实例并行 | 开多个进程同时刷，速度成倍提升 |
| 自动验证 | 刷完自动重新扫描确认 |

---

## 2. 文件说明

### 🌟 推荐：单文件版（新手首选）

仓库根目录只有**一个** Python 文件，认准它就行：

| 文件 | 角色 | 说明 |
|---|---|---|
| `ewt_brush_optimized.py` | 🌟 **单文件完整版** | 引擎+界面合并，**无需其他文件**。图形化菜单、自动装依赖、3种登录、作业总览、任务详情、刷课模式可选 |

```bash
python ewt_brush_optimized.py
```

> ✅ 不会再出现「找不到主脚本」问题——因为只有一个文件。

### 📦 历史版本（都在 legacy/ 文件夹）

| 文件夹 | 文件 | 说明 |
|---|---|---|
| `legacy/v3/` | ewt_brush_optimized.py + ewt_brush_optimized.py | V3 正式版 |
| `legacy/v3-test/` | ewt_brush_v3_test.py + easy_v3_test.py | v3-test 测试版 |
| `legacy/v2/` | ewt_brush_v2.py + ewt_brush_easy.py | V2 稳定版（只刷视频）|
| `original/` | spark.py | 原作者脚本（存档）|

用法（以 V3 为例）：

```bash
cd legacy/v3
python ewt_brush_optimized.py
```

> ⚠️ 历史版本的**两个文件需放同一目录**运行（easy 会自动找同目录引擎）。

### 🏆 选哪个？

- **单文件版**（推荐）：一个文件搞定，功能最全，新手最省心。
- **V3 正式版**：双文件模式，功能与单文件版一致。
- **V2 稳定版**：只刷视频课时，不处理 FM/板报。

### 什么是 FM 课时？

EWT 作业里除了视频课时，还有一小类「心灵成长/生涯规划」音频（平台叫 FM，2~6 分钟一条）。

- **单文件版 / V3**：通过 `updateMission` 接口直接直写完成
- **V2**：只处理视频（contentType 1/11），不处理 FM

### 为什么历史版本的 easy「遥控器」那么小？

`ewt_brush_optimized.py` 里全是「调度活」，一行刷课代码都没有：

| easy 的函数 | 干什么 |
|---|---|
| `ask / ask_int` | 问你问题（账号、密码、配置）|
| `scan_tasks` | 调引擎 `--dry-run` 扫描课时清单 |
| `build_cmd / start_instances` | 拼命令行并启动引擎子进程 |
| `monitor` | 读引擎日志，实时统计完成/错误/WAF |
| `main` | 串起整个流程（提问→扫描→启动→监控→验证）|

真正的大头全在**引擎**（60+ 个函数）：AES 加密登录、HMAC-SHA1 签名、令牌桶限速、竞态爆发、WAF 冷却重试、token 续期、弹题绕过、看课检测三重机制、FM/板报直写、clog 补发……

> 💡 **单文件版把两者合并了**，所以不存在「放在同一目录」的问题。

---

## 3. 傻瓜式用法（电脑 & 手机 & iPhone）

> Windows / macOS / Linux / 安卓 / iPhone 用同一个脚本，区别只在**怎么装 Python**。先看完通用流程，再按你的设备选下面的：电脑 3.1 / 安卓手机 3.2 / iPhone 3.3。

### 通用流程（各端一样）
```
运行 ewt_brush_optimized.py（单文件版）→ 选登录方式 → 自动扫描 → 选任务范围 → 输配置 → 开刷
【第 1 步】账号 / 密码        ← 输入你的账号密码（下次自动记住）
【第 2 步】识别任务           ← 自动扫描，**完整列出所有未完成课时**（不省略，全部显示）
【第 3 步】刷课配置           ← 实例数 / concurrency / burst / qps（直接回车用推荐值）
确认开始？                    ← 输入 Y 回车
```
> 💡 **单文件版**会先显示**作业完成情况总览**（每个作业的进度条），再让你选刷课范围。
之后全自动：启动 → 实时显示进度 → 全部完成 → 自动验证 → 显示"🎉 全部刷完"。

---

### 3.1 🖥️ 电脑端（Windows / macOS / Linux）

> 三个系统用同一个脚本，区别只是**怎么装 Python**。先找到你的系统：

| 你的电脑 | 看哪一节 |
|---|---|
| Windows | 3.1.1 |
| **Mac（苹果电脑）** | **3.1.2** |
| Linux | 3.1.3 |

装好 Python 后，统一跳到本节末尾的「✅ 通用步骤：直接运行（依赖自动装）」。

#### 3.1.1 Windows

**① 安装 Python（3.10 以上）**

到 [python.org](https://www.python.org/downloads/) 下载安装包 → 安装时**务必勾选 "Add Python to PATH"** → 装完打开"命令提示符"（Win+R 输入 `cmd`）验证：

```bat
python --version
```

看到 `Python 3.x.x` 即成功。

> ⚠️ 如果提示"不是内部或外部命令"，说明没勾 PATH。重新运行安装包 → 选 "Modify" → 把 "Add Python to PATH" 勾上 → 再验证。

#### 3.1.2 macOS（苹果电脑）

**① 安装 Homebrew（macOS 的软件包管理器，只需装一次）**

打开「终端」（按 `Command + 空格`，输入"终端"或"Terminal"），粘贴运行：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

> - 中途会要求输入**电脑登录密码**，输入时屏幕不显示任何字符，这是正常的，输完回车等它跑完。
> - Apple 芯片（M1/M2/M3/M4）装完后可能提示执行类似 `echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile` 的命令，**照抄执行**即可。

**② 用 Homebrew 安装 Python**

```bash
brew install python
```

**③ 验证**

```bash
python3 --version
```

看到 `Python 3.1x.x` 即成功。

> 💡 macOS 自带一个 `python3`，但版本较老、pip 环境不完整，**建议按上面用 Homebrew 装一个干净的**。
> 💡 如果 `brew install python` 卡在 "Updating Homebrew" 很久，按 `Ctrl + C` 取消更新，再重跑一次通常就能装上。
> 💡 装完如果 `python3` 提示找不到，重开一个终端窗口，或执行上一步 `brew shellenv` 那行命令。
> 💡 Apple 芯片用户注意：终端里命令走的是原生 arm64，无需 Rosetta，直接照上面操作即可。

#### 3.1.3 Linux

**① 安装 Python**

```bash
# Ubuntu / Debian 系
sudo apt update
sudo apt install -y python3 python3-pip
```

**② 验证**

```bash
python3 --version
```

> 其他发行版：
> - Fedora / CentOS / RHEL：`sudo dnf install -y python3 python3-pip`
> - Arch / Manjaro：`sudo pacman -S python python-pip`
> - 大多数桌面发行版已自带 python3，可跳过安装、只做验证。

#### ✅ 通用步骤：直接运行（依赖自动装）

**① 把脚本放到一个文件夹**

把 `ewt_brush_optimized.py`（单文件版）放到一个文件夹，例如：

- Windows：`C:\ewt`
- macOS / Linux：`~/ewt`

> 💡 **只需这一个文件**，不需要 `requirements.txt`，也不用手动装任何东西。

**② 直接运行（依赖会自动安装）**

```bash
cd 你的脚本目录          # 例如 Windows: cd C:\ewt   /  Mac/Linux: cd ~/ewt

# Windows 用：
python ewt_brush_optimized.py

# macOS / Linux 用：
python3 ewt_brush_optimized.py
```

**首次运行会自动检测并安装依赖**，你会看到：

```
  ==========================================================
   📦 检测到缺少运行所需的组件，正在自动安装…
      · httpx
      · pycryptodome
  ==========================================================
   （只需安装一次，请稍候，约 10~60 秒）
   ✅ httpx 安装成功
   ✅ pycryptodome 安装成功

  🎉 组件全部就绪，即将启动程序…
```

> 脚本会自动尝试多种安装方式（`pip` / `pip --user` / `pip3`），**Windows、macOS、Linux、Termux 全兼容**，通常不用你操心。

**③ 若自动安装失败（少见）**

脚本会打印出可直接照抄的手动命令，形如：

```bash
python3 -m pip install httpx pycryptodome

# 权限不足就加 --user：
python3 -m pip install --user httpx pycryptodome
```

装完再运行一次脚本即可。

> ⚠️ 常见失败原因：Python 是精简版（缺 pip）、或公司/学校网络受限。先确认 `python3 -m pip --version` 能正常输出。

**④ 手动验证（可选）**

```bash
python3 -c "import httpx, Crypto; print('OK')"
```

看到 `OK` 即依赖齐全。

<details>
<summary>🔧 进阶：用 requirements.txt 手动装（可选，一般用不到）</summary>

仓库也带了 `requirements.txt`（列出全部 2 个依赖），想手动装的话：

```bash
pip3 install -r requirements.txt       # 或
pip3 install httpx pycryptodome
```

内容如下（缺一不可）：

```
httpx>=0.24.0        # 网络请求库，负责与 EWT 服务器通信
pycryptodome>=3.19.0 # AES 加密库，负责登录密码加密
```

- `httpx` 是异步 HTTP 客户端，所有 API 请求都靠它
- `pycryptodome` 提供 `Crypto` 模块，登录时用 AES-CBC 加密密码

</details>

---

### 3.2 📱 手机端（Termux 推荐 / Pydroid3 备选）

#### 方案一：Termux（推荐，命令行体验与电脑一致，本次从零完整讲解）

---
**📦 什么是 Termux？**
Termux 是手机上的一款 Linux 终端模拟器，可以在手机上运行 Python 等程序。**首次配置需要几步，跟着下面做一次，之后每次直接运行即可。**

---

**① 安装 Termux（选对来源很重要）**

> ⚠️ **不要用 Google Play 商店的 Termux**（早已停止更新，装不了 Python）。以下二选一：

- **推荐：F-Droid 应用商店**
  1. 手机浏览器打开 `https://f-droid.org/F-Droid.apk` 下载安装 F-Droid
  2. 打开 F-Droid，搜索 **Termux** → 安装
  > 首次打开 F-Droid 可能提示"允许安装未知来源"，到手机设置里允许即可

- **备选：GitHub Releases 直接下 APK**
  1. 浏览器打开 `https://github.com/termux/termux-app/releases`
  2. 下载最新版 `termux-app_v0.118.0+github-debug_arm64-v8a.apk`（第3个是普通 ARM64 机型通用的）
  3. 安装

---

**② 首次打开 Termux（初始化 + 更新软件源）**

打开 Termux 后先做一次全面更新（首次更新较慢，请耐心，通常 1~5 分钟）：

```bash
pkg update && pkg upgrade -y
```

> 如果这步卡住或很慢（常见于国内网络），**先换国内源**，再重试上面的更新：
> ```bash
> # 一键切换到清华源（自动下载源配置）
> sed -i 's@^\(deb.*stable main\)$@#\1\ndeb [trusted=yes] https://mirrors.tuna.tsinghua.edu.cn/termux/termux-packages-24 stable main@' $PREFIX/etc/apt/sources.list
> pkg update -y
> ```
> 换源后再跑一次 `pkg upgrade -y`。
> > 🔄 若日后需要换回官方源，把 `sources.list` 里的 `mirrors.tuna...` 改回 `termux.net` 即可。

---

**③ 安装 Python（依赖不用管，脚本会自动装）**
```bash
pkg install -y python            # 只需装 Python 3，依赖交给脚本自动处理
```
> 💡 **跑脚本时它会自动检测并安装 httpx / pycryptodome**，不用你手动 pip。
> 💡 Termux 里 Python 命令是 `python`（电脑端是 `python3`）。

**✅ 验证 Python（可选）：**
```bash
python --version
```

**⚠️ 常见问题：**
- 若脚本提示自动安装失败，手动补一句：`pip install httpx pycryptodome`
- 若报 `No module named httpx`，说明依赖没装上，重跑脚本会自动重试

**④ 授权存储访问（关键步骤）**

Termux 默认访问不了手机存储，需要授权：
```bash
termux-setup-storage
```
> 手机会弹窗询问权限，选**允许**。成功后会在 Termux 主目录生成 `storage` 软链接：
> - `/data/data/com.termux/files/home/storage/shared` → 手机共享存储
> - **手机下载/共享目录的固定路径**：`/sdcard/Download` 或 `/storage/emulated/0/Download` 是同一个位置

---

**⑤ 把脚本放到手机 + 进入目录**

把 `ewt_brush_optimized.py`（单文件版）**拷到手机**（如 `Download/ewt360` 文件夹）。

然后在 Termux 里 `cd` 到脚本目录：
```bash
cd /storage/emulated/0/Download/ewt360    # 换成你放脚本的文件夹
ls                                       # 确认能看到两个 .py 文件
```
> 💡 提示：通常手机连接电脑 USB 拷贝、或手机文件管理器移动，都比在 Termux 里敲命令方便。

---

**⑥ 运行刷课（傻瓜入口）**

```bash
python ewt_brush_optimized.py       # V3 推荐（带进度条面板 + FM/板报直写）
# 或正式版：
python ewt_brush_optimized.py
```
按提示答题：**账号 → 密码 → 自动扫描（会完整列出全部课时）→ 实例/concurrency/burst/qps（回车用推荐值）→ Y 确认**，之后全自动。

---

**⑦ 防止息屏断网（刷课必备！）**

手机息屏后 Termux 可能被系统杀掉或断网，导致刷课中断。务必做这几步：

```bash
termux-wake-lock        # 保持 CPU 唤醒（息屏也能继续运行）
```
> 刷完后解除：`termux-wake-unlock`

同时去**手机设置**里：
1. 设置 → 应用 → Termux → 电池 → 选择**不限/不优化**（关闭电池优化）
2. 设置 → 应用 → Termux → 允许**后台运行**
3. 建议**保持亮屏并插电**刷课（最稳妥）

---

**⑧ 常驻运行（选做，刷大量课时更省心）**

如果课时很多想挂着通宵刷，可用 `nohup` 让脚本在后台跑，即使退出了 Termux 窗口也不停：
```bash
cd /storage/emulated/0/Download/ewt360
nohup python ewt_brush_optimized.py > run.log 2>&1 &
```
之后随时查看进度：
```bash
tail -f run.log          # 实时看刷课日志
# 按 Ctrl+C 停止查看日志（脚本继续后台跑）
```
> 停止整个后台刷课：`pkill -f ewt_brush`（慎用，会中断所有实例）

---

**⑨ 二次使用（之后每天只用这三步）**
```bash
termux-wake-lock                              # 1. 保持唤醒
cd /storage/emulated/0/Download/ewt360        # 2. 进目录
python ewt_brush_optimized.py                  # 3. 开刷（已完成的自动跳过）
```

---

#### 方案二：Pydroid3（图形界面，适合不熟悉命令行）

1. 应用商店安装 **Pydroid 3**（免费版即可）
2. 打开 → 菜单 → **Pip** → 输入 `httpx pycryptodome` → 安装
3. 把 `ewt_brush_optimized.py` 和 `ewt_brush_optimized.py` 拷贝到手机**公共存储**（如 `Download/`，**不要放 Pydroid 私有目录**），Pydroid 菜单 → 打开文件 → 选 `ewt_brush_optimized.py`
4. 点运行按钮即可（交互式提问照常显示）
5. 注意：Pydroid 是前台应用，**息屏可能暂停**，建议刷课时保持亮屏并插电

#### 手机端注意事项

| 事项 | 说明 |
|---|---|
| token 路径 | 傻瓜入口**已自动处理**（存 /tmp），无需手动设置 `EWT_TOKEN_FILE` |
| 网络 | 手机 IP 与电脑不同，风控独立；Wi-Fi 不稳定建议用流量 |
| 性能 | 低端机建议降配：实例数 1、concurrency 6、burst 8、qps 200 |
| 息屏 | Termux 用 `termux-wake-lock`；Pydroid 保持亮屏插电 |
| 电量 | 刷课耗电明显，务必插电 |
| 验证 | 脚本自动完成，看到"🎉 全部刷完"即完成 |

---

### 3.3 🍎 iPhone / iPad（iOS）

> iOS 系统限制严格，**没有安卓 Termux 那样的原生终端**，但可以用免费 App **iSH**（Alpine Linux 模拟器）跑起来。
> 先说结论：**能用，但比安卓慢**（iSH 是模拟运行）。本脚本是网络密集型，可正常刷课，只是启动略慢、必须保持前台。

#### 方案一：iSH（免费，推荐）

**① 安装 App**

App Store 搜索 **iSH Shell** → 下载安装（免费）。

**② 打开 iSH，换国内源（可选，加速）**

```sh
sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories
```

**③ 安装 Python 和 pip**

```sh
apk update
apk add python3 py3-pip
```

**④ 验证**

```sh
python3 --version
```

**⑤ 依赖：脚本会自动装（无需手动）**

安装好 Python 后，**直接运行脚本，它会自动检测并安装 httpx / pycryptodome**。

> 💡 pycryptodome 官方提供 Alpine 用的 musllinux 预编译包，iSH 里可直接装，**无需编译**。
> ⚠️ 若自动安装失败（网络慢），手动加国内镜像装：
> ```sh
> pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple httpx pycryptodome
> ```

**⑥ 把脚本放进 iSH**

两种方式任选：

- **方式 A（用「文件」App）**

  1. 在 iOS「文件」App 里把 `ewt_brush_optimized.py` 存到「我的 iPhone」
  2. 回到 iSH 执行：

  ```sh
  mkdir -p /root/ewt
  ls /mnt/root/                       # 查看「我的 iPhone」里的实际文件名
  cp "/mnt/root/ewt_brush_optimized.py" /root/ewt/
  cd /root/ewt && ls
  ```

  > iSH 里「我的 iPhone」的路径一般是 `/mnt/root/`；找不到就先用 `ls /mnt/root/` 看看。

- **方式 B（直接用 curl 下载）**

  ```sh
  mkdir -p /root/ewt && cd /root/ewt
  curl -L -o ewt_brush_optimized.py "https://raw.githubusercontent.com/Zoan0404/ewt360-brush/main/ewt_brush_optimized.py"
  ls -la
  ```

**⑦ 运行**

```sh
cd /root/ewt
python3 ewt_brush_optimized.py
```

之后按屏幕提示：选登录方式 → 自动扫描 → 选刷课范围 → 输配置 → 开刷。

#### 方案二：Pythonista（付费 App，约 ¥68）

- 内置 Python 3 + pip，能直接编辑运行 `.py`，界面友好
- ⚠️ **但它装不了带 C 扩展的 `pycryptodome`**，会导致账号密码登录的 AES 加密失败
- 因此**不推荐**用它跑本脚本，除非你只用「手动粘贴 token」登录

#### ⚠️ iOS 注意事项

| 事项 | 说明 |
|---|---|
| **必须保持前台** | iOS 会冻结后台 App，刷课期间 **iSH 要一直开着**，别切走、别锁屏 |
| 自动锁屏 | 设置 → 显示与亮度 → 自动锁定 → 改成「永不」，刷完记得改回 |
| 锁屏会断 | 锁屏后 iSH 被暂停，任务中断；重新打开会继续（进度不丢） |
| 耗电 | 刷课期间务必插电，屏幕常亮很费电 |
| 速度 | iSH 为模拟运行，比安卓 Termux 慢，属正常现象 |
| 网络 | 手机 IP 与电脑不同，风控独立；Wi-Fi 不稳建议用流量 |
| **最省心方案** | 有电脑/安卓机时，**建议用它们刷**，iPhone 只看进度 |

> 一句话总结：**iPhone 能跑（用 iSH），但更适合当"查看进度"的工具；真正长时间刷课，建议用电脑或安卓。**

---

### 3.4 📊 如何查看进度（重点！）

刷课过程中随时可以查看进度，三种方式任选：

#### 方式一：傻瓜入口自动显示（ewt_brush_optimized.py V3）

**V3 入口（ewt_brush_optimized.py）** 刷课期间**实时清屏重绘一个"实时刷课面板"**（默认每 3 秒自动刷新），带**每个课时的独立进度条** + **总进度条**，长这样：

```
  ═══════ 实时刷课面板 ═══════
  ⏱ 03m25s  运行 4 实例  错误 0  WAF 0  进度停滞: 否  刷新:3s
  📊 总进度: ██████████░░░░░░░░░░  47.0%  (47/100 课时完成)
  ── 实例 1 ──
    ▶ [鸦片战争            ] ██████████░░░░░░░░░░  47.1%  已播1270s/还需1430s
    ✅ [甲午战争            ] ████████████████████  完成
  ── 实例 2 ──
    ▶ [新文化运动          ] ███░░░░░░░░░░░░░░░░░  15.0%  已播300s/还需1700s
    ...
```

- `📊 总进度: ████… 47.0% (47/100 课时完成)` = **整个作业的总体进度**（已完成课时数/总课时数）
- 每个实例下面列出它**正在刷的每个课时**，一根进度条对应一个课时，实时显示播放百分比 + 已播/还需秒数
- `✅ … 完成` = 该课时已刷完
- `进度停滞: ⚠` = 连续多次刷新没新增完成，可留意网络
- 状态栏末尾 `刷新:3s` = 当前自动刷新间隔

> 🎛️ **实时调整刷新（监控时输入）**：
> - 输入数字 **1~30** 回车 → 调整刷新间隔（如 `5` 回车 = 每 5 秒刷新）
> - 直接按 **回车** → **立即刷新一次**（不用等倒计时）
> - 输入 **q** 回车 → 退出监控（后台实例继续刷）
>
> 顶部会提示：`📌 监控时输入：数字1-30=调刷新间隔(秒) | 回车=立即刷新 | q=退出监控（后台继续刷）`

**【V3 傻瓜入口（ewt_brush_optimized.py）】** 实时进度条面板（见上方）。
```
⏱ 03m25s  已完成 47/193  错误 0  WAF 0  运行中 4 实例
```

> 想暂停/查看？按 `Ctrl+C` 会暂停刷新（**后台实例继续刷**），输入 `q` 退出监控或直接回车继续。

#### 方式二：网页版实时面板（ewt_brush_web.py）

浏览器打开后第 ③ 卡片就是进度面板，**每 3 秒自动刷新**：
```
状态 / 已完成 / 总数 / 错误 / WAF / 耗时 / 运行实例
```
状态含义：`空闲 → 扫描中… → 刷课中… → 验证中… → 结束`，最后显示"🎉 全部刷完"或剩余课时清单。

#### 方式三：直接看日志文件（进阶）

每个实例的完整日志实时写入文件，可随时查看明细：

| 入口 | 日志位置 |
|---|---|
| 傻瓜入口 easy | `/tmp/ewt_easy_logs/inst_0.log`、`inst_1.log`…（每个实例一个） |
| 网页版 web | `/tmp/ewt_web_logs/inst_0.log`… |

```bash
# 实时滚动查看某个实例的日志（Ctrl+C 退出）
tail -f /tmp/ewt_easy_logs/inst_0.log

# 只看已完成/进行中的课时
grep "\[完成\]" /tmp/ewt_easy_logs/inst_0.log
grep "▶"       /tmp/ewt_easy_logs/inst_0.log

# 统计已完成数量
grep -c "\[完成\]" /tmp/ewt_easy_logs/inst_*.log
```

**日志行格式解读**（v2 引擎输出）：
```
▶ [123456] 历史-鸦片战争 [22分54秒] 开始刷课          ← 开始
[进度][123456] 第3轮 已播12:34 还需10:20 请求120 成功118  ← 每轮推进
[完成][123456] 累加920s                                  ← 该课时刷完
[错误] 连接失败…                                        ← 该课时失败（会补刷）
[通过] 看课检测已通过                                    ← 检测通过
⚠ 看课检测未通过（第1/3次），3s 后自动重刷…              ← 机制C 自动重刷
```

#### 如何判断"刷完了"？

1. **自动验证**：所有实例退出后，工具自动重新扫描，显示"🎉 全部课时已刷完！"即完成
2. **手动验证**（任何时候都可以）：
   ```bash
   python ewt_brush_optimized.py --dry-run --account 你的账号 --password 你的密码
   ```
   看到 `没有未完成的课时（可能已全部刷完）` = 全部完成 ✅

#### 中途中断/关机会丢进度吗？

不会。已刷完的课时服务器已记录，**下次运行扫描会自动跳过已完成**，只刷剩下的，不重不漏。重新运行 `python ewt_brush_optimized.py` 即可续刷。

---

## 4. 概念详解：刷课到底在刷什么

### 4.1 作业（Homework）
老师布置的整套任务，有唯一 ID（如 `10516876`）。一个作业里包含多个学科、多个课时。

### 4.2 课时（Lesson）
一个具体的视频课，有唯一 lessonId。比如"历史-鸦片战争 22分54秒"就是一个课时。
**任务 = 把所有未完成的课时刷成已完成。**

### 4.3 必学科目（MustLearn）
每个学生真实选科不同，脚本只刷你**必学**的科目（自动识别，不用管）。

### 4.4 token（登录凭证）
登录后服务器发给你的"身份证"（格式 `用户ID-类型-加密串`）。脚本存在 token 文件里，下次运行直接复用，不用重新登录。
- 电脑默认存 `/root/ewt_token.txt`，手机用环境变量指定（本工具已自动处理）
- **多实例必须共用同一个 token 文件**，否则各自登录会互相踢下线（本工具已自动处理）

### 4.5 播放上报（核心原理）
官方播放器每 10 秒向服务器上报一次"我看到第 X 秒了"。服务器累计上报时间，达到视频总时长就判定完成。

脚本做的事：**模拟这个上报协议**，让你"看到"的秒数飞速增长。

### 4.6 竞态爆发（burst，加速的关键）
服务端有一个限流机制："检查剩余额度 → 扣减"，但这个"检查+扣减"不是原子的（有间隙）。
**技巧**：一个课时内部，同时发 N 条上报请求（N=burst 值），所有请求在 30 毫秒窗口内同时到达，多数请求都能"滑过"限流检查 → 等效 5 倍加速。

> 通俗理解：闸机一次只放一个人过，但 12 个人同时挤，闸机反应不过来，一下全过去了。

### 4.7 WAF 风控
服务器会检测异常流量，拦截时返回 `429 安全威胁`。脚本检测到会自动**冷却 120 秒再重试**（最多 2 次）。
**实测结论**：WAF 不易触发，不限速也安全。

### 4.8 看课检测（三重兜底）
平台会抽查你是否真的在看，脚本内置三重机制应对：
- **机制 A**：视频中途弹题（防挂机）→ 自动获取题目并提交答案，解除暂停
- **机制 B**：看课检测点（seriousCheck）→ 用 addVideoss 接口两步时序（scr=0 → scr=2）直接置为"通过"
- **机制 C**：刷完检测未通过 → 自动重刷（最多 3 次）

### 4.9 FM 课时（心灵成长 / 生涯规划音频）
作业里有一小类**短音频**（2~6 分钟），平台归类为 FM（内容类型 contentType 3/5，科目显示"心灵成长/生涯规划"）。

**测试版引擎**扫描时自动识别 contentType=3/5 的 FM/板报课时，调用 EWT 的 `updateMission {schoolId, contentId, contentType, percent:1}` 接口**一次直写完成度 100%**（不走播放心跳、秒完成），刷课日志显示 `[直写] ... updateMission(ct=3) → ✅ 100%`。

- **V3 正式版**（`ewt_brush_optimized.py` / `ewt_brush_optimized.py`）：✅ 自动直写 FM/板报
- **V2 稳定版**（`legacy/v2/`）：不处理 FM（只扫 contentType 1/11）

---

## 5. 参数详解：每个数字是什么意思

### 5.1 实例数（Instance）
**同时启动几个刷课进程**。**测试版不限制上限**，自行决定。
- 1 个实例 = 一台"刷课机器"（**新手推荐，最稳**）
- 多实例 = 多台机器同时干，速度叠加（但**不稳定、不好操控，不建议新手追求**）
- 每个实例刷不同的课时（自动分片，互不重复）

### 5.2 外层路数 concurrency（并行课时数）
**一个实例同时刷几个课时**。默认 12，**无上限，自行决定**。
- 12 = 12 个课时同时推进
- **18 = 新手推荐**（实测 18 路 + burst48 3 分 21 秒刷完 400 分钟视频，稳定）
- 更高路数 = 更快但注意网络波动
- 多实例时每实例可独立设置，但建议保持一致

### 5.3 内层路数 burst（单课时爆发并发）
**一个课时内部，一次同时发多少条上报请求**。默认 12，**无上限，自行决定**。
- 12 = 默认，每轮推进约 40 秒
- 24 = 提速明显，每轮推进 50~90 秒
- **48 = 新手推荐**（实测 48 高路数稳定，配合 18 路极速）
- 每 10 秒发一轮，burst 越高单轮推进越多

### 5.4 qps（全局限速，请求/分钟）
**每秒最多发多少个请求**。默认 400，**测试版建议不限速**。
- `100000` = **不限速（推荐）**！实测 WAF 不易触发
- `400` = 稳妥限速（需要限速时用）
- ⚠️ **陷阱**：填 `0` 并不会不限速！脚本代码 `if qps and qps > 0` 导致 qps=0 时不生效，反而退化为默认 120/分钟（更慢）。本工具已自动把 0 改成 100000。

### 5.5 其他参数（高级用户用）

| 参数 | 作用 |
|---|---|
| `--dry-run` | 只扫描不刷课（本工具第 2 步自动执行） |
| `--hw 10516876` | 只刷指定作业 |
| `--offset/--limit` | 分片：起始下标 + 数量（多实例自动计算） |
| `--phase-offset 5000` | 错峰毫秒，多实例避免首轮爆发撞车（自动加） |
| `--speed 2.0` | 官方倍速模式（不用竞态爆发时），**2.0 是硬上限**，2.1 报错 |
| `--force-rounds 3` | 强制重刷 N 轮（修复看课检测用） |
| `--force-all` | **强制重刷全部课时（含已完成）**：扫描不过滤已完成，每个课时至少跑 2 轮（可配 `--force-rounds` 改轮数） |

---

## 6. 效率指标：刷课时长 ÷ 视频总时长

**怎么算效率**：`刷课时长 ÷ 实际视频总时长`，**该值越小，效率越高**。

举例：刷 100 个课时，视频总时长 40 小时（144000 秒），实际刷课花了 21 分钟（1286 秒）：
```
效率 = 1286 ÷ 144000 = 0.0089
```
意思：**刷 1 小时视频只需要 32 秒**。

### 实测数据（最新实测，含高路数单实例）

| 配置 | 效率 RATIO | 相当于 |
|---|---|---|
| 单实例 12路/qps400 | ≈ 0.029 | 刷1小时视频需 1.7 分钟 |
| **4实例 × 12路 + 不限速** | ≈ 0.0089 | 刷1小时视频仅需 32 秒 |
| **单实例 18路 + burst48 + 不限速** | **≈ 0.0021** | **刷 1 小时视频仅需 7.6 秒** ⭐⭐ |

**💥 最新实测验证（单实例高路数）**：
> `并行路数: 18 | QPS: 100000 | 竞态爆发: 48路` → **407 分钟视频（1578min39s）仅用 3 分 21 秒刷完**，123 个课时全部一次通过，无重刷、无卡顿！
>
> 配置：`python ewt_brush_optimized.py --concurrency 18 --burst 48 --qps 100000`（单实例）

**结论**：
- **新手强烈建议用"单实例 不限速 + 高路数"**（如 18路 + burst48 + qps100000），稳定、易操控、无需开多个终端
- 多实例并行虽然理论更快，但**不稳定、不好操控**（多个进程、登录风控、手动分片），**不建议新手追求**
- 单实例高配置已经足够快（3分21秒刷完400分钟视频），完全够用

---

## 7. 推荐配置速查（照着填就行）

> ⚠️ **新手直接抄第 1 行！** 多实例（第 3 行）不稳定且需手动操作，**不建议新手追求**。

| 场景 | 实例数 | concurrency | burst | qps |
|---|---|---|---|---|
| 🟢 **新手推荐（单实例高路数，最稳）** | **1** | **18** | **48** | **100000** |
| 🟢 日常稳妥 | 1 | 12 | 12 | 400 |
| 🔵 推荐满速（单实例） | 1 | 14 | 36 | 100000 |
| 🟣 极速多实例（进阶）| 4 | 12 | 24 | 100000 |
| 🔴 极限测试 | 1~2 | 18 | 48 | 100000 |
| 🟡 网络差/低配机 | 1 | 6 | 8 | 200 |

> **新手建议**：就用**单实例 18路 + burst48 + 不限速**，实测 400 分钟视频 3 分 21 秒刷完，稳定且不用管多实例。
> 课时很多想再快 → 再考虑多实例（但先确保单实例跑通）。

---

## 8. 多实例并行原理（为什么要开多个）

### 分片（Sharding）
假设有 100 个课时、4 个实例，自动切成 4 片：
```
实例1: offset 0,  limit 25   → 刷第 1~25 个
实例2: offset 25, limit 25   → 刷第 26~50 个
实例3: offset 50, limit 25   → 刷第 51~75 个
实例4: offset 75, limit 0    → 刷第 76~100 个（0=刷到末尾）
```

### 错峰（Phase Offset）
多个实例同时启动会"首轮爆发撞车"（同一瞬间同时发大量请求），所以每个实例错开 5 秒启动（实例2 错 5s、实例3 错 10s、实例4 错 15s），本工具自动处理。

### 三个坑（本工具已自动规避）
1. **环境变量必须逐个传**：`export` 只对第一个进程生效，后面进程读不到 token 文件会各自重新登录互相踢 → 本工具用 `env` 逐个传给每个实例 ✅
2. **共用 token 文件**：所有实例共用一个 token，避免互踢 ✅
3. **已完成自动跳过**：中途重启不重不漏，已完成的课时扫描时自动过滤 ✅

---

## 9. 脚本自己会处理的事（不用你操心）

| 情况 | 自动处理 |
|---|---|
| token 失效 / 被挤下线（2001106） | 自动重新登录换新 token，最多 3 次 |
| WAF 拦截（429 安全威胁） | 冷却 120 秒自动重试，最多 2 次 |
| 视频中途弹题 | 自动答题解除暂停 |
| 看课检测未通过 | **机制C 自动重刷，最多 3 次**（第2次起强制3轮触发 addVideoss）；通过后自动清理后台标记 |
| 单课时最终失败（连接错误等） | 本工具**自动补刷**：验证发现剩余 → 询问后原配置直接补刷，最多 3 轮 |
| 多实例互踢 | 共用 token + 自动续期 |
| 刷完验证 | 自动重新扫描确认"没有未完成的课时" |

---

## 10. 常见问题 FAQ

| 现象 | 原因 | 处理 |
|---|---|---|
| `✗ 获取学校信息失败`（空消息） | 网络波动 | 重跑即可（偶发） |
| `Token 已失效/被挤下线（2001106）` | 别处登录/多实例互踢 | 脚本自动续期；单实例可避免 |
| `EWT 网关 429「安全威胁」` | IP 被风控标记 | 自动冷却重试；频繁则降低配置 |
| `speed 超限（699001）` | speed > 2.0 | 保持 ≤2.0 |
| `连接被拒绝` | 并发过高 | 降到 12路 或更低 |
| `没有未完成的课时` | **全部刷完 ✅** | 无需操作，等新作业发布 |
| 想重刷已完成的课时 | 扫描默认跳过已完成 | 用 `--force-all`，详见第 12 章 |
| 作业显示还有 FM 课时没完成（心灵成长/生涯规划） | 正式版只刷视频 | 用**单文件版**（`ewt_brush_optimized.py`）自动直写 FM/板报 |
| 刷完显示"未通过" | 看课检测问题 | **无需操作**：机制C 自动重刷最多3次；仍不行本工具自动补刷 |
| Windows UnicodeEncodeError（中文乱码）| 控制台编码问题 | 脚本已内置 UTF-8 加固，直接运行即可；若仍报错，PowerShell 执行 `$env:PYTHONUTF8="1" ; py ewt_brush_optimized.py`，CMD 执行 `set PYTHONUTF8=1 && py ewt_brush_optimized.py` |
| 单个课时失败（连接/WAF超限） | 偶发网络/风控 | **无需操作**：本工具自动补刷（最多3轮），已完成的自动跳过 |
| macOS 提示 `command not found: brew` | 没装 Homebrew | 按 3.1.2 先装 Homebrew，或重开终端 |
| macOS 提示 `command not found: python3` | Python 未装/路径未生效 | 重开终端，或执行 `brew shellenv` 那行命令 |
| iPhone（iSH）装 pycryptodome 失败 | 网络/pip 源问题 | 加国内源重装：`pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple httpx pycryptodome` |
| iPhone 刷一会儿就停了 | iOS 冻结了后台 App | **iSH 必须保持前台**，设置里把自动锁定改为"永不" |
| iPhone 用 Pythonista 登录失败 | 它装不了 pycryptodome | 改用 iSH，或只用"手动粘贴 token"登录 |

---

## 11. 安全提示

- 脚本直连 EWT 官方接口，与浏览器行为一致，**历史全程 0 封禁**
- **不要外泄账号密码/token**
- 建议避开 EWT 高峰期刷课，降低风控概率
- 若连续多次 429，暂停 10~30 分钟再继续
- 本工具只刷你**自己**的账号，安全设计

---

## 12. 强制重刷所有课时（高级）

> 正常情况下工具**只刷未完成**的课时（已完成的自动跳过）。如果因为看课检测状态异常、或你就是想全部重刷一遍，用下面的方法。

### 12.1 为什么默认刷不了已完成的课时？
两个过滤：① 扫描时 `list_video_tasks` 默认跳过 `finished=True` 的课时；② 即使传入了，`needed<=0` 也会直接判定完成跳过。所以要重刷必须**同时**解除这两层：`--force-all`（解除扫描过滤）+ `force_rounds>0`（强制跑轮），`--force-all` 已自动处理两者（默认每课时至少跑 2 轮）。

### 12.2 视频/校本课时：`--force-all`

```bash
# 强制重刷全部课时（默认每课时至少2轮）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 --force-all \
    --concurrency 12 --burst 24 --qps 100000

# 指定作业 + 指定轮数（更彻底：每课时强制3轮）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 --hw 10516876 \
    --force-all --force-rounds 3 --concurrency 12 --burst 24 --qps 100000

# 先预览会重刷哪些（--force-all --dry-run 会列出含已完成的全部课时）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 --force-all --dry-run

# 多实例分片重刷（每实例都加 --force-all，分片基于"全部课时"列表）
python ewt_brush_optimized.py --account X --password Y --force-all \
    --concurrency 12 --burst 24 --qps 100000 --offset 0 --limit 28
python ewt_brush_optimized.py --account X --password Y --force-all \
    --concurrency 12 --burst 24 --qps 100000 --offset 28 --limit 28 --phase-offset 5000
```

### 12.3 FM 课时（心灵成长/生涯规划音频）

**V3 引擎 `ewt_brush_optimized.py` 已内置 FM/板报直写** —— 通过 `updateMission` 接口一次直写 100%，无需额外 FM 脚本：

```bash
# 只刷未完成的 FM（自动跳过已完成）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码

# 强制重刷全部 FM（含已完成）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 --force-all
```

**工作原理**：测试版引擎扫描时会自动识别 FM(contentType=3)/板报(contentType=5) 课时，调用 EWT 的 `updateMission {schoolId, contentId, contentType, percent:1}` 接口**一次直写完成度 100%**，不走播放心跳、秒完成。

> 📌 FM 直写在刷课时自动处理（每个 FM 课时日志显示 `[直写] ... updateMission(ct=3) → ✅ 100%`）。

> ⚠️ 旧教程提到的 `ewt_fm_brush_tg.py` 是遗留文件，**当前版本已不再需要**（FM 直写已并入测试版引擎）。

### 12.4 注意事项
1. **强制重刷会产生新的播放记录**——无特殊需求不建议全刷，已完成课时服务器已记录
2. 典型用途：刷完后部分课时后台显示"看课检测未通过"、或想重置课时播放数据
3. 强制模式耗时 ≈ 全部课时数 × 轮数 × 10 秒 ÷ 并行数，课时多时建议用多实例
4. 试卷类课时（contentType 2）不是播放任务，刷课脚本不处理

---

## 附：命令行直用（进阶，不用傻瓜入口时）

```bash
# 预检扫描
python ewt_brush_optimized.py --dry-run --account 你的账号 --password 你的密码

# 单实例极速
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 \
    --concurrency 12 --burst 24 --qps 100000

# 多实例（4个）手动分片（终端1~4各跑一条）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 \
    --concurrency 12 --burst 24 --qps 100000 --offset 0 --limit 25
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 \
    --concurrency 12 --burst 24 --qps 100000 --offset 25 --limit 25 --phase-offset 5000
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 \
    --concurrency 12 --burst 24 --qps 100000 --offset 50 --limit 25 --phase-offset 10000
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 \
    --concurrency 12 --burst 24 --qps 100000 --offset 75 --limit 0 --phase-offset 15000

# FM 课时（心灵成长/生涯规划音频）——用测试版引擎自动直写（含 FM/板报）
python ewt_brush_optimized.py --account 你的账号 --password 你的密码 \
    --concurrency 12 --burst 24 --qps 100000
# 或傻瓜入口：
python ewt_brush_optimized.py

# 查看全部参数
python ewt_brush_optimized.py --help
# 查看 V3 参数：python ewt_brush_optimized.py --help
```
