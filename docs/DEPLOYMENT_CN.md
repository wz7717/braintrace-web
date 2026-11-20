# 旧版 Windows HTTP 与 CLI 部署说明

本页适用于用 `site_server.py` 启动的旧版 Windows HTTP 服务和配套 CLI。Streamlit Community Cloud 的入口、Linux 环境及队列限制见 [Streamlit 部署指南](STREAMLIT_CLOUD.md)。

## 1. 目录和版本

- 源码根目录包括 HTTP 服务、CLI、科学推断代码、配置模板和文档。
- `runtime_assets/` 提供同版人源绑定文件、猕猴冻结模型、120 套参考、映射和示例。完整人源 CEL 推断需要同版完整人源资产。使用分析复现包时，请按归档根 README 获取单独提供的人源文件。
- `assembled_runtime/` 是组装后使用的运行目录。源目录和资产目录各自保留。

应用来源为[固定提交 2bf9563](https://github.com/wz7717/braintrace-web/tree/2bf9563cef8190f0483e23a4d54f7e6466fe6c77)。资产版号 `20261109_120_beams_local_v1` 可与 `runtime_assets/ASSET_EDITION.json`、`metadata/SCHEME.json` 和[版本记录](../resources/VERSION.json)对照。

## 2. 环境

Windows 科学工作环境使用 Python 3.11.9、NumPy 1.26.4、pandas 2.2.3、SciPy 1.13.1、scikit-learn 1.5.2、joblib 1.5.3 和 threadpoolctl 3.6.0。需要配置依赖时，可在相应 Python 环境中运行 `python -m pip install -r requirements.txt`。人源实时 CEL 还需 R 4.6.1 UCRT 和固定 R 包。[人源运行环境](HUMAN_BUNDLE_SETUP.md)

## 3. 组装运行目录

从源码根目录执行。若资产目录放在其他位置，在 `--assets` 填写其实际路径。

~~~powershell
python -X utf8 -B tools/prepare_runtime.py --assets runtime_assets --out ../assembled_runtime
~~~

输出的父目录应已存在。为 `--out` 选择源码和资产目录之外的一个新目录。组装工具检查版本和路径冲突，将源码与 `runtime_assets/` 复制为运行目录所需的相对布局。配置环境、运行推断和复现研究各有单独入口。

## 4. 本机启动

~~~powershell
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
~~~

打开 `http://127.0.0.1:8766/`。旧版 HTTP 服务默认监听本机地址。也可从运行目录使用 `./launch_site.ps1 -ScientificPython <固定python.exe的路径> -Port 8766`。

人源实时推断使用运行目录下的 `runtime.local.json`。从 `runtime.example.json` 复制一份后，填写本机 `python`、`rscript`、`rlib`、可选的 `rlib_site` 和已存在的 ASCII `temp_root`。等价环境变量为 `BRAINTRACE_PYTHON`、`BRAINTRACE_RSCRIPT`、`BRAINTRACE_RLIB`、`BRAINTRACE_RLIB_SITE` 和 `BRAINTRACE_TEMP_ROOT`。配置保存在部署主机。选择已保存的示例时页面显示原输出。实时入口和不带 `--saved` 的 CLI 会运行模型。

## 5. 匿名队列和反向代理

旧版 HTTP 服务包含匿名浏览器会话、会话和 IP 限额、单进程 FIFO、进程超时回收及结果过期。同一浏览器会话共享限额。[旧版 HTTP 队列与默认限额](ANONYMOUS_QUEUE.md)

本机服务使用专用的非公开工作目录。人源 CEL 路线要求该目录使用 ASCII 路径。

~~~powershell
python -X utf8 -B site_server.py --port 8766 --work-root C:/BrainTraceWork/anonymous_queue
~~~

需要自定义限额时，可复制 `queue.example.json` 为实例专用的 `queue.local.json`，并指定 `--queue-config queue.local.json`。

通过域名提供旧版 HTTP 服务时，可由同机 HTTPS 反向代理转发到 `127.0.0.1`。

~~~powershell
python -X utf8 -B site_server.py --port 8766 --work-root C:/BrainTraceWork/anonymous_queue --public-origin https://your-host.example --trust-proxy-client-ip
~~~

`--public-origin` 使用域名根路径的 HTTPS origin，省略路径与末尾斜杠。配置 `deployment/Caddyfile.example` 时，将 `BRAINTRACE_DEMO_HOST` 设置为实际域名。代理保留 Host，用连接的客户端地址覆盖 `X-BrainTrace-Client-IP`。应用仅在启用该选项且 Host 与域名配置匹配时信任此地址。代理前还有 CDN 时，按实际可信代理链配置客户端地址。

在目标主机配置 DNS、TLS、服务账户、进程管理和目录权限。可运行 `caddy validate --config Caddyfile --adapter caddyfile` 检查模板语法。此模板采用匿名会话，后端端口与运行目录保留在主机侧，公共 HTTPS 会话 Cookie 带 Secure、HttpOnly 和 SameSite。保持单应用实例。重启前下载所需结果，重启会清除内存任务和会话。[Caddy 反向代理说明](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)

## 6. 运行资产和示例

本版 120 套参考均由 Ensembl 97 源队列重建。下层按无序 Network Top3 组合查找对应参考。成年 PsychENCODE common-annotation 输入使用独立映射契约。[输入步骤](PSYCHENCODE_INPUT.md)

HTTP 资源页按 `resources/FILES.json` 列出运行目录内的文档、基因轴、映射和猕猴 GEO 示例。人源 CEL 从 GEO 取得，来源和 SHA-256 见 [GEO_CEL_SOURCE.json](../GEO_CEL_SOURCE.json)。人源冻结资产按预测绑定校验，资产内历史路径用于追溯来源。模型、派生参考及第三方示例依各自条款使用。[数据及许可](DATA_AND_LICENSES.md)

## 7. 更新和回退

升级时使用同一版的源码和资产组装新运行目录，配置该目录的 `runtime.local.json`，再切换启动路径。回退时可恢复上一版保留的目录和启动命令。全研究复现按研究归档的独立流程运行。

## 历史验收

旧版 Windows HTTP 的队列、资源取件和单样本验收记录见[代码来源与验收记录](CODE_PROVENANCE.md)。原反向代理交付范围为模板与本机配置流程。该阶段的记录保留了域名访问、代理限额和运行环境的待验收范围。历史 PsychENCODE 例用于检查输入适配和参考查找。各记录列明其样本、环境和未验证范围。
