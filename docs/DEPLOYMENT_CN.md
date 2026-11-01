# 部署说明：源码与运行资产分开

本次 Streamlit Community Cloud 入口、Linux 环境与匿名限额以 [STREAMLIT_CLOUD.md](STREAMLIT_CLOUD.md) 为准。下文保留原 Windows HTTP/CLI 服务步骤；不能将其 loopback 服务器入口直接填写为 Streamlit 应用入口。

## 1. 交付布局

- github/：候选 GitHub 源码，前端、HTTP/CLI 后端、科学推断代码、配置模板和文档。
- runtime_assets/：服务器资产，完整人类绑定文件、猕猴冻结模型、43 套下层参考、映射及示例。
- assembled_runtime/：由复制工具新建的运行目录；不提交 GitHub。

现有 wz7717/braintrace-web 私有仓库保留上一版源码；本匿名队列版只在本地另存，尚未上传。运行资产复用既有独立目录，未部署服务。
源目录单独启动时会说明缺少资产。资产不靠 Git LFS 隐式下载，也没有虚构公开下载地址。

## 2. 准备环境

优先使用现有固定环境：Python 3.11.9；numpy1.26.4、pandas2.2.3、scipy1.13.1、
scikit-learn1.5.2、joblib1.5.3、threadpoolctl3.6.0。版本见 requirements.txt。
如接收方在新环境安装，可执行 `python -m pip install -r requirements.txt`；该命令不随组装自动执行。
无需 Node、npm 或前端构建。猕猴推断不需要 R。
人类实时 CEL 需要 R4.6.1(ucrt)及固定 R 包，见 HUMAN_BUNDLE_SETUP.md；不能把固定 Windows 环境称作已在 Linux/容器验证。

## 3. 复制组装，不修改源文件

在仓库根目录打开终端，使用固定 Python（将单独取得的 runtime_assets 放在仓库旁边，或在 --assets 中填写其实际位置）：

```text
python -X utf8 -B tools/prepare_runtime.py --assets ../runtime_assets --out ../assembled_runtime
```

输出父目录须存在，输出目录须不存在，并位于源码/资产目录之外。程序检查版本标识及路径冲突后复制文件。
它不建立符号链接，不安装环境，不训练、推断、重建参考或重算性能。已有输出会被拒绝，不覆盖旧目录。
代码在 github/science，数值资产在 runtime_assets/science；组装后恢复原科学实现期望的相对路径。
runtime_assets/ASSET_EDITION.json 与 github/metadata/SCHEME.json 标识 `20261101_43_beams_psychencode_v1`。

## 4. 本机启动

```text
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
```

打开 http://127.0.0.1:8766/ 。默认仅监听本机，不自动对外开放。
Windows 也可运行 `./launch_site.ps1 -ScientificPython <固定python.exe的路径> -Port 8766`。
人类实时推断：在运行目录将 runtime.example.json 复制为 runtime.local.json，填写本机 python、rscript、rlib、
rlib_site（可空）和已存在的 ASCII temp_root。配置必须留在服务器，不提交 GitHub。
等价环境变量为 BRAINTRACE_PYTHON、BRAINTRACE_RSCRIPT、BRAINTRACE_RLIB、BRAINTRACE_RLIB_SITE、BRAINTRACE_TEMP_ROOT。

保存示例只读取已保存输出；“实时推断”和 CLI 未带 --saved 的命令会运行模型。
本版检查范围见 ANONYMOUS_QUEUE.md 和 CODE_PROVENANCE.md；既有科学验证按未变范围复用，不重跑队列。

## 5. 免登录队列与将来部署（本轮不执行）

当前新版另存为 anonymous_queue_20261101，尚未同步到现有私有 GitHub 仓库。
已具备独立匿名浏览器会话、按会话和 IP 限额、单进程 FIFO、超时回收及结果过期。
具体默认值、会话边界和恢复行为见 [ANONYMOUS_QUEUE.md](ANONYMOUS_QUEUE.md)。

本地启动示例（工作目录必须为专用私有目录；人类路线要求 ASCII 路径）：

```text
python -X utf8 -B site_server.py --port 8766 --work-root C:/BrainTraceWork/anonymous_queue
```

需要自定义限额时，复制 queue.example.json 为私有 queue.local.json，再追加
`--queue-config queue.local.json`。不需要账户数据库；同一浏览器共享匿名会话。

以后部署时，Python 仍只监听 127.0.0.1，由同机 HTTPS 代理转发所有路径：

```text
python -X utf8 -B site_server.py --port 8766 --work-root C:/BrainTraceWork/anonymous_queue --public-origin https://实际域名 --trust-proxy-client-ip
```

public-origin 必须是不含路径或末尾斜杠的 HTTPS origin；按域名根路径部署。
deployment/Caddyfile.example 为免登录模板，配置真实 BRAINTRACE_DEMO_HOST。
代理保留 Host，强制用连接客户端地址覆盖 X-BrainTrace-Client-IP；应用仅在显式开启该选项、
且 Host 是配置域名时信任此单 IP 头。不要将客户端提供的同名头直接转发。
若代理前面另有 CDN，此模板只会识别 CDN 地址，需要先按实际可信链配置，不能盲目信任 X-Forwarded-For。

部署者需在目标机器配置 DNS、TLS、服务账户、进程管理和目录权限；
可以先运行 `caddy validate --config Caddyfile --adapter caddyfile` 检查模板替换后的语法。
该模板没有 basic_auth，也没有将后端端口或运行目录静态公开；Cookie 在公共 HTTPS 下带 Secure/HttpOnly/SameSite。
只启动一个应用实例，不增加 Web worker 数量。重启丢失内存任务和会话；先下载结果。
域名访问、代理限额和运行环境仍需真实服务器验收。本轮没有部署、安装代理或公网测试。

参考：[Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)。

## 6. 运行资产与下载链接

43 套参考是原 37 套加成年分析已完成的 6 套原文件，未重建。旧模型、原参考和评分函数不改。
新增组合被选中时可找到对应参考；尚未覆盖的组合仍返回 reference_unavailable，不寻找近似参考。
PsychENCODE 公共 common-annotation 背景和映射不同，现已接入独立契约；不能伪造原两种 mapping_version。输入步骤见 PSYCHENCODE_INPUT.md。

resources/FILES.json 只允许运行目录内文件。资源页链接到文档、基因轴、三种映射和示例；
所有包外 ../ 路径、完整 ZIP、旧稿件下载入口均移除。完整复现包和最新版稿件由作者另行提供。
如以后有真实外部下载地址，应显式更新资源页，不能把本机路径写成公共 URL。

完整人类 bundle 保留原冻结身份和历史路径元数据，不能删掉四份绑定文件或改写它们来脱敏。
模型、来源派生参考及第三方示例的公开再分发安排仍按组件处理。源码/资产分离不等于这些授权已经完成。

## 7. 更新和回退

未来更新到新 source/asset edition 时，另建新运行目录，修改自己的 runtime.local.json，再切换启动路径。
旧运行目录保留，可恢复原启动命令；本轮不切换现有服务。不执行全研究训练或 FULL 作为部署步骤。
已完成的针对性接入检查见 CODE_PROVENANCE.md；上传时未重新执行模型推断或科学验证。

Current PsychENCODE interface: see PSYCHENCODE_INPUT.md. Two example paths cover old/new reference lookup; no full-cohort rerun, model fitting or performance estimation.
