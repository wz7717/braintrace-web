# 部署说明：源码与运行资产分开

## 1. 交付布局

- github/：候选 GitHub 源码，前端、HTTP/CLI 后端、科学推断代码、配置模板和文档。
- runtime_assets/：服务器资产，完整人类绑定文件、猕猴冻结模型、43 套下层参考、映射及示例。
- assembled_runtime/：由复制工具新建的运行目录；不提交 GitHub。

当前仓库仅同步原 github 目录的源码，初建为 wz7717/braintrace-web 私有仓库；服务器运行资产单独保留，未部署网页服务。
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
本次新增检查限两个 PsychENCODE 样本的输入适配和三层输出对照，其他已通过检查按未变范围复用，不重跑队列。

## 5. 实际域名部署模板（本轮未执行）

后端继续监听 127.0.0.1；同一主机上的 HTTPS 代理转发所有路径至 127.0.0.1:8766。
在运行目录启动 `python -X utf8 -B site_server.py --port 8766 --public-origin https://实际域名`。
public-origin 必须为完整 HTTPS origin，不含路径或末尾斜杠。仅显式配置的 Host/Origin 获准；不采用任意转发头推断。
URL 根路径部署，例如 https://demo.example.org/；当前前端用绝对路径，未实现 /braintrace/ 子路径部署。

deployment/Caddyfile.example 是待填写模板：把源码模板复制为服务器私有 Caddyfile，配置实际域名、用户名和 bcrypt 密码哈希。
也可用模板中的 BRAINTRACE_DEMO_HOST、BRAINTRACE_DEMO_USER、BRAINTRACE_DEMO_PASSWORD_HASH 环境变量；
使用 `caddy hash-password` 交互生成哈希。代理保留浏览器 Host 与 Origin，无需改写成 localhost。
先运行 `caddy validate --config Caddyfile --adapter caddyfile`，再按实际服务器方式启动 Caddy。
真实域名、DNS、TLS、凭据及进程管理均由部署者配置；本轮没有安装 Caddy 或执行这些步骤。

这是单进程、单推断工作线程、内存队列的研究 demo。上传和结果约 30 分钟清理，重启会丢失未下载结果。
支持小范围受控访问；没有独立用户账号/任务隔离、持久化队列或多实例共享状态。勿以多 worker 分散内存任务。
同一服务会话 token 用于请求来源检查，不是用户身份认证；模板在 HTTPS 代理层配置访问账号。
后端端口不直接暴露公网，代理只转发 HTTP，不对运行目录启用静态文件服务。
真正上线前需在目标机器确认域名访问与所需实时推断可用；这里没有把接口检查当作线上验收。

参考：[Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)、
[Caddy basic_auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth)。

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
