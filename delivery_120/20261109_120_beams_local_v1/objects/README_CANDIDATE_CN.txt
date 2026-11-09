BrainTrace 120 套参考本地应用候选

此目录供检查。网页入口为 streamlit_app.py，装配资源根为 runtime_assets/。使用候选自带的版本固定文件、现有安装约定及对应运行环境。

猕猴内置运行和下载均由 EXAMPLES.json 的两条 GEO 记录给出。分别为 GSE128537 的 10_10 和 GSE179328 的 LID_100660。PsychENCODE 保留 26,514 行共同注释用户上传路线，沿已批准映射和 ID 轴。AMY、HIP两个内置示例留在原本地材料。

人类现场示例的装配前提

按 GEO_CEL_SOURCE.json，从 GEO 的 GSM755211 补充文件入口取得原 GSM755211.CEL.gz，并按所列既有身份确认。把原件放到 runtime_assets/examples/human/GSM755211.CEL.gz 后再用现场示例。候选中提供取得指引和原保存对照；这一步实际取件另行登记。普通用户上传继续使用原人类输入合同。

固定资产和装配位置

源侧 metadata/SCHEME.json 与资产侧 ASSET_EDITION.json 同步至 20261109_120_beams_local_v1。科学 scheme ID 沿用原版。43 套原参考完整保留，追加 77 套由历史冻结下层资产转换的参考。有效 Top3 可查全 120 个组合。下层输出仍需兼容输入及可评估信号，未知输入的端到端可用率待独立验证。原 PsychENCODE 指南保留于 notices/，候选展示版置于 docs/，每个装配相对路径各一份。三份 Bo 原始处理源按既定范围排除。

NOTICE.txt、licenses/、notices/ 和 CANDIDATE_MANIFEST.json 沿用原候选，记录其原许可和身份范围。新版组装记录见上一级 ASSEMBLY_RECEIPT_20261109.json。此次仅准备本地候选，运行验收另行登记。
