# BrainTrace Streamlit 部署版

入口为 `streamlit_app.py`，保留人类 CEL 的 RAW_FIXED/RANK_FIXED 实时推断，以及含成年 PsychENCODE 适配的猕猴 Network/Group/Exact 三层推断。

本地网页包以 wz7717/braintrace-web 的 main（ca445528）为底本。源码和同版 runtime_assets/ 一起使用。猕猴冻结模型、原 43 套参考和 77 套历史冻结参考转换件的版本见 resources/VERSION.json。

在 Streamlit Community Cloud 选择本仓库、`main` 分支、`streamlit_app.py` 和 Python **3.11**。依赖由 `requirements.txt`、`requirements-lock.txt`、`packages.txt` 指定。首次启动会构建独立 R 4.6.1 与 Python 3.11.9 科学工作进程；主界面的 Python 不替换冻结计算环境。具体步骤和实际云端验收见 [部署说明](docs/STREAMLIT_CLOUD.md)。

匿名页面采用单机 FIFO 队列、每会话及全站限额、任务/结果归属校验和超时进程树回收。人类上传上限 80 MiB，gzip 展开上限 256 MiB；猕猴上传上限 8 MiB，并在解析前限制 NPZ 声明大小及 CSV/TSV 记录数。匿名会话不等于真实身份，免费单实例也不能承受无限并发上传；详见 [安全范围](SECURITY.md)。

冻结科学规则、模型参数和原有科学结果未改。已有验证继续复用，本次只做输入边界、匿名队列、界面和依赖的针对性检查，不重训或重跑完整队列。历史验证与本轮检查在 [代码来源](docs/CODE_PROVENANCE.md) 中分开记录。

随包提供 GSE128537（10_10）和 GSE179328（LID_100660）的已准备输入。GSM755211.CEL.gz 请从 [GEO 原记录](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM755211) 获取，并按 [GEO_CEL_SOURCE.json](GEO_CEL_SOURCE.json) 核对 SHA-256。启动后可选人源路线上传。若要从页面直接运行人源示例，请在启动前把 CEL 放入 runtime_assets/examples/human/，如已启动则重启。

原 Windows HTTP/CLI 工具继续保留。使用原兼容环境，在新目录组装：

```text
python -X utf8 -B tools/prepare_runtime.py --assets runtime_assets --out ../assembled_runtime
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
```

打开 `http://127.0.0.1:8766/`。组装只复制文件，不推断、不覆盖输入目录。原 Windows 服务不作为 Streamlit Cloud 入口。

输入规范见 [INPUT_FORMATS](docs/INPUT_FORMATS.md) 与 [PSYCHENCODE_INPUT](docs/PSYCHENCODE_INPUT.md)。5000 基因输入仅支持 Network。120 套参考覆盖全部无序 Network Top3 组合，下层结果仍取决于输入与可评估信号。结果是候选排序，Group 集合命中不等于 Exact 精确定位。

用户上传、结果、凭据、本机配置、日志、环境二进制、私有编辑材料及完整复现压缩包不进入仓库。现有许可与待落实权限见 [DATA_AND_LICENSES](docs/DATA_AND_LICENSES.md)，不将整包自动解释为 MIT。
