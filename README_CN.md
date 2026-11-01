# BrainTrace Streamlit 部署版

入口为 `streamlit_app.py`，保留人类 CEL 的 RAW_FIXED/RANK_FIXED 实时推断，以及含成年 PsychENCODE 适配的猕猴 Network/Group/Exact 三层推断。

本次私有仓库同步同时包含网页代码和独立的 `runtime_assets/` 子目录；运行需要两者。模型、映射及 43 套下层参考原样保留。这是网页推断应用，不是完整科研复现包。上传 GitHub 不等于网站已经部署，也不意味着运行资产可以公开再分发。

在 Streamlit Community Cloud 选择本仓库、`main` 分支、`streamlit_app.py` 和 Python **3.11**。依赖由 `requirements.txt`、`requirements-lock.txt`、`packages.txt` 指定。首次启动会构建独立 R 4.6.1 与 Python 3.11.9 科学工作进程；主界面的 Python 不替换冻结计算环境。具体步骤和实际云端验收见 [部署说明](docs/STREAMLIT_CLOUD.md)。本轮只同步 GitHub，不部署。

匿名页面采用单机 FIFO 队列、每会话及全站限额、任务/结果归属校验和超时进程树回收。人类上传上限 80 MiB，gzip 展开上限 256 MiB；猕猴上传上限 8 MiB，并在解析前限制 NPZ 声明大小及 CSV/TSV 记录数。匿名会话不等于真实身份，免费单实例也不能承受无限并发上传；详见 [安全范围](SECURITY.md)。

冻结科学规则、模型参数和原有科学结果未改。已有验证继续复用，本次只做输入边界、匿名队列、界面和依赖的针对性检查，不重训或重跑完整队列。历史验证与本轮检查在 [代码来源](docs/CODE_PROVENANCE.md) 中分开记录。

原 Windows HTTP/CLI 工具继续保留。使用原兼容环境，在新目录组装：

```text
python -X utf8 -B tools/prepare_runtime.py --assets runtime_assets --out ../assembled_runtime
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
```

打开 `http://127.0.0.1:8766/`。组装只复制文件，不推断、不覆盖输入目录。原 Windows 服务不作为 Streamlit Cloud 入口。

输入规范见 [INPUT_FORMATS](docs/INPUT_FORMATS.md) 与 [PSYCHENCODE_INPUT](docs/PSYCHENCODE_INPUT.md)。5000 基因输入仅支持 Network；43 套参考不代表全部候选组合或 110 细区均已验证。结果是候选排序，Group 集合命中不等于 Exact 精确定位。

用户上传、结果、凭据、本机配置、日志、环境二进制、私有编辑材料及完整复现压缩包不进入仓库。`runtime_assets/README_ASSETS_CN.txt` 原样保留了上一阶段“不提交 GitHub”的打包说明；那是当时未授权上传的状态，本次仅按新授权同步到私有仓库。现有许可与待落实权限见 [DATA_AND_LICENSES](docs/DATA_AND_LICENSES.md)，不将整包自动解释为 MIT。
