'use strict';

// UI localization only. Model IDs, API requests and exported numeric data stay invariant.
let language = 'en';
try { language = localStorage.getItem('braintrace-language') === 'zh' ? 'zh' : 'en'; } catch {}
const messages = {
  "转录组参考": "TRANSCRIPTOMIC REFERENCE",
  "冻结设计": "FROZEN BY DESIGN",
  "科研演示": "RESEARCH DEMO",
  "单样本科研工作台": "SINGLE-SAMPLE WORKBENCH",
  "如何阅读结果": "HOW TO READ THE OUTPUT",
  "结果语境": "RESULT CONTEXT",
  "BrainTrace / 参考说明": "BRAINTRACE / REFERENCE",
  "BrainTrace 本地科研工作台：使用冻结参考模型进行真实单样本脑区候选排序。": "BrainTrace local research workbench: rank candidate brain regions from a single sample with frozen reference models.",
  "BrainTrace · 单样本科研工作台": "BrainTrace · Single-sample workbench",
  "跳转到工作台": "Skip to workbench",
  "BrainTrace 首页": "BrainTrace home",
  "研究工作台": "RESEARCH WORKBENCH",
  "工作台导航": "Workbench navigation",
  "单样本推断": "Single-sample inference",
  "已验证示例": "Verified examples",
  "输入规范": "Input guide",
  "模型与适用范围": "Models & scope",
  "选择参考模型": "REFERENCE MODEL",
  "参考物种": "Reference species",
  "人类 · 9 个支持脑区": "9 supported regions",
  "猕猴 · 10 个支持脑区": "10 supported regions",
  "沿用冻结参考、预处理与模型参数。每次只处理一个样本。": "Fixed reference, preprocessing and model parameters. One sample per request.",
  "不训练 · 不调参": "No training · No tuning",
  "本地预览": "Local preview",
  "· 仅在此电脑运行": "· On this computer only",
  "研究工具": "Research tools",
  "模型说明": "Model guide",
  "从一个样本，追溯脑区候选": "One sample. Explore its brain-region candidates",
  "。": ".",
  "将表达谱与冻结参考模型对照，探索粗粒度脑区排序及完整模型分数。": "Compare an expression profile with frozen reference models to explore coarse regional rankings and complete model scores.",
  "当前模型概况": "Current reference model",
  "支持脑区": "Supported regions",
  "模型特征": "Model features",
  "新增拟合": "New fits",
  "分析步骤": "Analysis steps",
  "准备样本": "Prepare sample",
  "选择示例或上传文件": "Choose an example or upload",
  "冻结推断": "Frozen inference",
  "应用既有模型与参数": "Apply saved models and parameters",
  "探索结果": "Explore results",
  "查看候选与完整分数": "Inspect candidates and all scores",
  "准备单样本": "Prepare a single sample",
  "检测运行环境…": "Checking runtime…",
  "运行模式": "Inference mode",
  "实时推断": "Live inference",
  "查看保存示例": "View saved example",
  "冻结配置": "Frozen configuration",
  "样本来源": "Sample source",
  "使用已验证示例": "Use verified example",
  "上传我的样本": "Upload my sample",
  "真实样本": "Real sample",
  "原保存输出可复核": "Saved output available",
  "下载示例输入": "Download example input",
  "样本 ID": "Sample ID",
  "仅用作输出标识，不影响分数": "Output identifier only; does not affect scores",
  "1–128 位字母、数字、下划线、点或短横线；以字母或数字开头。": "1–128 ASCII letters, digits, underscores, dots or hyphens; start with a letter or digit.",
  "拖入一个文件，或": "Drop one file, or",
  "点击选择": "browse files",
  "移除文件": "Remove file",
  "正在连接本地服务…": "Connecting to local service…",
  "运行冻结推断": "Run frozen inference",
  "原保存输出 · 不执行推断": "Saved output · No inference performed",
  "查看随 demo 保存的已验证示例。切换至“实时推断”可运行同一个样本，并逐类别对照原结果。": "These are the original saved example outputs. Choose Live inference to run the same sample and compare every class with the original result.",
  "让输入与模型匹配": "Match your input to the model",
  "查看完整输入规范": "Read the full input guide",
  "分数用于支持类别内的候选排序，": "Scores rank candidates within the supported classes; they are ",
  "不是解剖定位正确率": "not anatomical accuracy estimates",
  "。不支持脑区、cfRNA 混合样本与患者诊断不在本 demo 范围内。": ". Unsupported regions, cfRNA mixtures and patient diagnosis are outside this demo's scope.",
  "模型说明与证据边界": "Model scope and evidence limits",
  "等待任务": "Waiting for a task",
  "候选脑区": "Candidate regions",
  "↓ 分数 CSV": "↓ Scores CSV",
  "↓ 结果 JSON": "↓ Result JSON",
  "下一个线索，从这里开始": "Your next clue starts here",
  "运行一个样本后，查看 Top 3 候选、完整类别分数与示例复核结果。": "Run one sample to inspect its top 3 candidates, all class scores and example comparisons.",
  "先查看已验证示例": "Explore a verified example",
  "结果配置": "Result configurations",
  "完整候选排序": "Complete candidate ranking",
  "模型分数": "Model score",
  "每个配置的分数在支持类别内归一化；条形按 0–1 固定尺度展示。": "Scores are normalized within each configuration's supported classes. Bars use a fixed 0–1 scale.",
  "保留结果的语境": "Keep the result in context",
  "Top 3 候选覆盖不等于 Top 1 正确。不同配置的最高分也不能用来事后选择“最佳”模型。": "Top 3 coverage does not imply Top 1 correctness. Do not use the highest score across configurations to select a model after seeing results.",
  "逐类别数值与原始输出": "Per-class values and raw output",
  "完整精度 · 类别 ID · 决策值": "Full precision · Class IDs · Decision values",
  "查看原始 JSON": "View raw JSON",
  "冻结参考 · 单样本 · 可追溯输出": "Frozen references · Single samples · Traceable outputs",
  "文件与已完成结果在 30 分钟后过期，请及时下载": "Files and completed results expire after 30 minutes. Download results to keep them.",
  "关闭说明": "Close guide",
  "此工作台需要 JavaScript。也可使用原 launch.ps1 启动 Streamlit 入口。": "This workbench requires JavaScript. You can also start the original Streamlit interface with launch.ps1.",
  "使用冻结来源尺度的表达值。": "Uses expression values on the frozen source scale.",
  "使用样本内部基因排序。": "Uses within-sample gene ranks.",
  "按预先选定的两套配置分别推断，不事后择优。": "Runs both configurations selected in advance, without post-hoc model selection.",
  "冻结来源尺度 + floor + clip。": "Frozen source scale + floor + clip.",
  "冻结来源尺度；不应用 floor / clip。": "Frozen source scale, without floor or clip.",
  "冻结来源尺度 + floor。该保存模型 C = 0.01。": "Frozen source scale + floor. This saved model uses C = 0.01.",
  "冻结来源尺度 + clip。": "Frozen source scale + clip.",
  "四套完整保存配置；不构成独立验证队列。": "Four complete saved configurations, not four independent validation cohorts.",
  "检查完成并入队": "Validated and queued",
  "开始冻结推断": "Inference started",
  "对照原输出": "Comparing saved output",
  "完成": "Completed",
  "失败": "Failed",
  "无法连接本地服务。请确认启动终端仍在运行，然后重试。": "Cannot reach the local service. Make sure the server is running, then try again.",
  "本地服务返回了无法读取的响应。请检查启动终端。": "The local service returned an unreadable response. Check the server terminal.",
  "请求未完成，请重试。": "The request could not be completed. Please try again.",
  "GSE128537 / GSM3679496 · 10_10 · 4,379 观测 / 621 缺失": "GSE128537 / GSM3679496 · 10_10 · 4,379 observed / 621 missing",
  "CEL / CEL.gz · 单个文件 · 最大 80 MiB": "CEL / CEL.gz · One file · Up to 80 MiB",
  "NPZ / CSV · 完整 5,000 基因 · 最大 8 MiB": "NPZ / CSV · Complete 5,000-gene panel · Up to 8 MiB",
  "我确认这是符合规范的成人 bulk-tissue Human Exon 1.0 ST CEL 样本。": "I confirm this is a compatible adult bulk-tissue Human Exon 1.0 ST CEL sample.",
  "我确认已按原基因映射，用完整计数库计算 ln(1 + CPM)，并提供显式缺失掩码；不是 TPM、log2 或仅面板归一化值。": "I confirm the established gene mapping and full-library ln(1 + CPM) preprocessing, with an explicit missing-feature mask; these are not TPM, log2 or panel-only normalized values.",
  "成人 bulk-tissue CEL": "Adult bulk-tissue CEL",
  "冻结 PLM 生成完整 16,295 基因轴，再应用保存的 200 特征模型。": "Frozen PLM generates the full 16,295-gene axis, then applies the saved 200-feature model.",
  "文件名不能证明平台、成人资格或解剖身份。": "A filename cannot establish platform compatibility, adult eligibility or anatomical identity.",
  "不接收任意表达矩阵、TPM 或其他芯片平台。": "Arbitrary expression matrices, TPM and other array platforms are not accepted.",
  "已准备的单样本": "One prepared sample",
  "5,000 基因 ln(1 + CPM)": "5,000-gene ln(1 + CPM)",
  "按完整计数库归一化，再选择固定基因面板。": "Normalize using the full count library before selecting the frozen gene panel.",
  "观测零值为 observed=1；缺失值为 observed=0，并应用冻结来源均值。": "A measured zero uses observed=1; an absent feature uses observed=0 and the frozen source mean.",
  "CSV 按 gene ID 对齐；NPZ 轴顺序须与模板一致。": "CSV rows align by gene ID; the NPZ axis must follow the template order.",
  "连接本地服务…": "Connecting…",
  "●  冻结环境可用": "●  Frozen runtime ready",
  "环境未就绪": "Runtime unavailable",
  "RAW_FIXED · 来源尺度": "RAW_FIXED · Source scale",
  "RANK_FIXED · 样本排序": "RANK_FIXED · Within-sample ranks",
  "RAW + RANK · 两套配置": "RAW + RANK · Both configurations",
  "全部四套保存配置": "All four saved configurations",
  "推断处理中": "Inference in progress",
  "输入与配置已锁定。完成后可切换或开始新任务。": "Inputs and configuration are locked until this task finishes.",
  "运行环境未就绪；可先查看保存示例。": "The runtime is unavailable. You can still view saved examples.",
  "运行真实单样本，并自动对照原保存输出。": "Run real single-sample inference and compare with the original saved output.",
  "文件正在上传与校验，请稍候。": "Uploading and validating the file. Please wait.",
  "选择一个符合规范的文件，先完成结构检查。": "Choose a compatible file to validate its structure first.",
  "文件检查完成，请确认样本与预处理符合规范。": "File checks passed. Confirm the sample and preprocessing meet the input contract.",
  "输入已就绪。将使用当前预先选择的冻结配置。": "Input is ready. The selected frozen configuration will be used.",
  "正在读取保存输出…": "Loading saved output…",
  "重试读取": "Retry loading",
  "仅接受 .CEL 或 .CEL.gz；普通 .gz 文件不符合规范。": "Only .CEL or .CEL.gz files are accepted; an arbitrary .gz file is not supported.",
  "接受原有 .NPZ/.CSV，或 PsychENCODE 单样本计数 .TSV/.CSV。": "Use prepared .NPZ/.CSV, or PsychENCODE single-profile counts in .TSV/.CSV.",
  "文件须非空且不超过 {limit} MiB。": "The file must be nonempty and no larger than {limit} MiB.",
  "请先填写有效的样本 ID，以字母或数字开头。": "Enter a valid sample ID beginning with a letter or digit.",
  "正在上传到本地推断服务…": "Uploading to the local inference service…",
  "文件上传进度": "File upload progress",
  "上传完成，正在校验结构…": "Upload complete. Validating structure…",
  "本地校验响应无效，请重新选择文件。": "The validation response is invalid. Please select the file again.",
  "校验失败，请检查输入。": "Validation failed. Please check the input.",
  "观测 {observed} / 缺失 {missing} · 全库计数 {library}": "Observed {observed} / Missing {missing} · Full-library count {library}",
  "上传连接中断，请重新选择文件。": "The upload connection was interrupted. Please select the file again.",
  "上传或校验超时，请重新选择文件。": "Upload or validation timed out. Please select the file again.",
  "正在提交本机任务": "Submitting local task",
  "等待服务确认，尚未报告推断完成。": "Waiting for service confirmation. Inference has not been reported as complete.",
  "任务未提交": "Task not submitted",
  "任务提交状态未确认": "Task submission unconfirmed",
  "没有启动新的推断。修正输入后可重试。": "No new inference was started. Correct the input and try again.",
  "重试时将使用同一个请求标识，避免重复推断。": "Retrying will reuse the same request identifier to avoid duplicate inference.",
  "任务已排队": "Task queued",
  " · 前方 {count} 个任务": " · {count} task(s) ahead",
  "正在运行冻结模型": "Running the frozen model",
  "单样本推断完成": "Single-sample inference complete",
  "本次推断未完成": "Inference did not complete",
  "仅显示服务端实际阶段，不估算完成百分比。": "Actual server stages only; no estimated completion percentage.",
  "真实任务记录": "Actual task record",
  "任务已过期或服务已重启": "Task expired or service restarted",
  "结果未保留在当前服务内。可重新提交样本。": "This result is no longer retained by the service. You can submit the sample again.",
  "当前任务可能仍在执行。": "The current task may still be running.",
  "重新连接": "Reconnect",
  "本次真实推断": "Live frozen inference",
  "原保存输出 · 未执行推断": "Saved output · No new inference",
  "样本": "Sample",
  "Human · 9 类": "Human · 9 classes",
  "Macaque · 10 类": "Macaque · 10 classes",
  "{count} 套预先选择配置": "Preselected configurations: {count}",
  "观测 {observed} / 缺失 {missing}": "Observed {observed} / Missing {missing}",
  "✓ 与原保存示例一致：类别轴与排序相同，最大数值差 {difference}（atol = {tolerance}，rtol = 0）。仅说明该示例本次推断一致。": "✓ Matches the saved example: identical class axes and rankings; maximum numerical difference {difference} (atol = {tolerance}, rtol = 0). This confirms agreement for this example run only.",
  "本次结果与原保存示例存在差异。保留下方真实输出，不报告为成功复现；请查看 JSON 中的逐配置比较。": "This run differs from the saved example. The actual output is retained below and is not reported as a successful reproduction. See the per-configuration comparisons in the JSON.",
  "候选": "CANDIDATE",
  "{count} 个支持类别": "{count} supported classes",
  "结果来源": "Result source",
  "本次冻结推断": "Live frozen inference",
  "已有示例输出": "Saved example output",
  "仅用于候选排序": "Candidate ranking only",
  "缺失特征处理": "Missing-feature handling",
  "冻结来源均值": "Frozen source means",
  "示例参考标签 · 不由预测分数推导": "Example reference label · Not derived from scores",
  "命中": "hit",
  "未命中": "miss",
  "包含": "included",
  "未包含": "not included",
  "此处不从模型最高分推导样本真实解剖标签，也不据此报告定位正确率。": "The highest model score is not used to infer an anatomical truth label or report localization accuracy.",
  "排序": "Rank",
  "类别 ID / 原标签": "Class ID / Original label",
  "决策值": "Decision value",
  "输入规范与示例文件": "Input guide & example files",
  "模型与证据边界": "Model scope & evidence limits",
  "查看随 demo 保留的原始说明（英文原文）": "View the original bundled documentation (English)",
  "样本 ID 已更改，等待重新校验…": "Sample ID changed. Waiting to revalidate…",
  "每次仅支持一个样本文件，请重新选择。": "Only one sample file is supported per request. Please select one file.",
  "请选择人类或猕猴参考模型。": "Select the human or macaque reference model.",
  "样本 ID 必须为文本。": "The sample ID must be text.",
  "样本 ID 需为 1–128 位英文字母、数字、下划线、点或短横线，并以字母或数字开头。": "The sample ID must contain 1–128 ASCII letters, digits, underscores, dots or hyphens, starting with a letter or digit.",
  "请选择有效的冻结配置。": "Select a valid frozen configuration.",
  "配置不可重复。": "Configurations must not be duplicated.",
  "文件名为空或过长。": "The filename is empty or too long.",
  "人类参考仅接受 .CEL 或 .CEL.gz，不接受任意 .gz 文件。": "The human reference accepts only .CEL or .CEL.gz files, not arbitrary .gz files.",
  "文件不是有效的 gzip 容器，请检查 CEL.gz 文件完整性。": "The file is not a valid gzip container. Check the CEL.gz file's integrity.",
  "扩展名与大小检查通过；CEL 内容、平台及模型绑定将在真实推断中校验。成人组织适用性需依据样本元数据确认。": "Extension and size checks passed. CEL contents, platform and model bindings are checked during live inference. Adult tissue eligibility must be confirmed from sample metadata.",
  "输入校验未通过。请使用完整的 5,000 基因 NPZ/CSV，检查字段、基因 ID、缺失掩码和全库总量。": "Input validation failed. Use a complete 5,000-gene NPZ/CSV and check the fields, gene IDs, missing-feature mask and full-library total.",
  "5,000 基因轴、单样本形状、数值与缺失掩码检查通过。预处理来源仍需由你确认。": "The 5,000-gene axis, single-sample shape, values and missing-feature mask passed validation. You must still confirm preprocessing provenance.",
  "待运行文件已达到本机缓存上限，请移除旧文件后重试。": "The local upload cache is full. Remove an older file and try again.",
  "请选择已验证示例或上传单样本。": "Choose a verified example or upload one sample.",
  "缺少有效请求标识，请刷新页面后重试。": "A valid request identifier is missing. Refresh the page and try again.",
  "同一请求标识不能用于不同输入。": "The same request identifier cannot be used for different inputs.",
  "当前环境未就绪。请按本地运行指南配置冻结 Python/R 环境；仍可查看保存示例。": "The frozen runtime is not ready. Configure Python/R according to the local guide. Saved examples remain available.",
  "任务队列已满，请等待当前推断完成。": "The task queue is full. Wait for the current inference to finish.",
  "请确认样本符合当前参考模型的输入规范。": "Confirm that the sample meets the selected reference model's input contract.",
  "文件缓存已过期或已移除，请重新选择文件。": "The uploaded file has expired or was removed. Please select it again.",
  "文件校验上下文与当前样本不一致，请重新选择文件。": "The file was validated for a different sample context. Please select it again.",
  "输入检查完成，已进入本机任务队列。": "Input checks completed. The task is in the local queue.",
  "正在执行冻结 CEL → PLM → 模型推断。": "Running the frozen CEL → PLM → model inference pipeline.",
  "正在应用冻结来源均值、尺度与所选配置，并计算候选分数。": "Applying frozen source means, scaling and the selected configuration to calculate candidate scores.",
  "正在与原保存输出逐类别比较分数、排序与类别轴。": "Comparing scores, rankings and class axes with the original saved output.",
  "真实推断完成。结果可查看及下载。": "Live inference completed. Results are ready to view and download.",
  "冻结推断未完成，未生成结果。请检查文件完整性、平台与冻结运行环境。": "Frozen inference did not complete; no result was generated. Check file integrity, platform compatibility and the frozen runtime.",
  "推断超过 180 秒，已终止该请求；未生成结果。": "Inference exceeded 180 seconds. The request was terminated and no result was generated.",
  "任务不存在或已过期。请重新运行；已下载的结果不受影响。": "The task does not exist or has expired. Run it again; downloaded results are unaffected.",
  "仅支持本机预览地址。": "Only the local preview address is supported.",
  "请求来源不匹配。": "The request origin does not match.",
  "本地会话已更新，请刷新页面。": "The local session has changed. Please refresh the page.",
  "请求大小无效或超出限制。": "The request size is invalid or exceeds the limit.",
  "上传未完成，请重新选择文件。": "The upload was incomplete. Please select the file again.",
  "文件不存在。": "The file does not exist.",
  "地址不存在。": "The address does not exist.",
  "请求必须为 JSON 对象。": "The request must be a JSON object.",
  "接口不存在。": "The endpoint does not exist.",
  "本地服务处理失败，请检查启动终端或重新启动服务。": "The local service could not process the request. Check the terminal or restart the service.",
  "界面语言": "Interface language",
  "<div class=\"contract-platform\">Human Exon 1.0 ST<br>成人 bulk-tissue CEL</div><div class=\"contract-formats\"><span class=\"format-tag\">.CEL</span><span class=\"format-tag\">.CEL.gz</span><span class=\"format-tag\">≤ 80 MiB</span></div><ul class=\"contract-bullets\"><li>冻结 PLM 生成完整 16,295 基因轴，再应用保存的 200 特征模型。</li><li>文件名不能证明平台、成人资格或解剖身份。</li><li>不接收任意表达矩阵、TPM 或其他芯片平台。</li></ul>": "<div class=\"contract-platform\">Human Exon 1.0 ST<br>Adult bulk-tissue CEL</div><div class=\"contract-formats\"><span class=\"format-tag\">.CEL</span><span class=\"format-tag\">.CEL.gz</span><span class=\"format-tag\">≤ 80 MiB</span></div><ul class=\"contract-bullets\"><li>Frozen PLM generates the full 16,295-gene axis, then applies the saved 200-feature model.</li><li>A filename cannot establish platform compatibility, adult eligibility or anatomical identity.</li><li>Arbitrary expression matrices, TPM and other array platforms are not accepted.</li></ul>",
  "<div class=\"contract-platform\">已准备的单样本<br>5,000 基因 ln(1 + CPM)</div><div class=\"contract-formats\"><span class=\"format-tag\">.NPZ</span><span class=\"format-tag\">.CSV</span><span class=\"format-tag\">≤ 8 MiB</span></div><ul class=\"contract-bullets\"><li>按完整计数库归一化，再选择固定基因面板。</li><li>观测零值为 observed=1；缺失值为 observed=0，并应用冻结来源均值。</li><li>CSV 按 gene ID 对齐；NPZ 轴顺序须与模板一致。</li></ul>": "<div class=\"contract-platform\">One prepared sample<br>5,000-gene ln(1 + CPM)</div><div class=\"contract-formats\"><span class=\"format-tag\">.NPZ</span><span class=\"format-tag\">.CSV</span><span class=\"format-tag\">≤ 8 MiB</span></div><ul class=\"contract-bullets\"><li>Normalize using the full count library before selecting the frozen gene panel.</li><li>A measured zero uses observed=1; an absent feature uses observed=0 and the frozen source mean.</li><li>CSV rows align by gene ID; the NPZ axis must follow the template order.</li></ul>"
};
const localizedText = new Map();
let bannerState = null;
let uploadView = null;
let openDoc = null;
Object.assign(messages,{"资源":"Resources","猕猴 · Network / Group / Exact":"10 Networks · Group / Exact","将表达谱与冻结参考模型对照，探索 Network 候选及受支持的 Group、Exact 独立排序。":"Compare one expression profile with frozen references. Explore Network candidates and, where supported, independent Group and Exact rankings.",
  "版本与资源": "Version & resources",
  "保存示例": "Saved example",
  "输入校验未通过。请检查 5,000 或 21,668 基因轴、单样本字段、缺失掩码与全库总量。": "Input validation failed. Check the 5,000 or 21,668 gene axis, single-sample fields, observed mask and full-library total.",
  "完整三层输入契约检查通过。原始数据及归一化来源仍需由你确认。": "The complete three-tier input contract passed. Confirm the original data and normalization provenance.",
  "Network 输入检查通过；下层输入不足或不兼容，仍可运行第一层。请查看缺项。": "Network input passed; lower input is insufficient or incompatible. Network can still run. See the missing requirements.",
  "NPZ / CSV · 5,000 或 21,668 基因 · 最大 8 MiB": "NPZ / CSV · 5,000 or 21,668 genes · Up to 8 MiB",
  "三层示例 · 完整 21,668 基因轴": "Three-tier example · Complete 21,668-gene axis",
  "当前方案：floor_clip + 原 Group / Exact。": "Current scheme: floor_clip + original Group / Exact.",
  "三层输入需要完整 21,668 基因轴及版本信息。5,000 基因输入只运行 Network。": "Three-tier input requires all 21,668 coordinates and version metadata. A 5,000-gene input runs Network only.",
  "下层输入状态": "Lower input status",
  "需提供": "Required",
  "候选筛选": "Candidate screening",
  "独立下层排序": "Independent lower-tier ranking",
  "Group 与 Exact 在同一个 Top3 Network 候选全集中独立排名；第一层分数不乘入下层。": "Group and Exact rank independently within the same Top3 Network candidate set. Network scores are not multiplied into lower scores.",
  "已完成": "Completed",
  "下层未运行：输入不足": "Not run: insufficient lower input",
  "下层未运行：输入不兼容": "Not run: incompatible lower input",
  "下层未运行：该候选组合的参考尚未提供": "Not run: reference for this candidate combination has not been provided",
  "下层运行失败": "Lower-tier inference failed",
  "下层不可评价：有效信号不足": "Lower tier not evaluable: insufficient valid signal",
  "成员细区": "Member regions",
  "成员数": "Member count",
  "原类别 ID": "Original class ID",
  "Pearson 相关系数（Top200 成员最高分）": "Pearson correlation (maximum member Top200 score)",
  "融合分数（0.25 × z50 + 0.75 × z100）": "Fusion score (0.25 × z50 + 0.75 × z100)",
  "下层分数不使用 0–1 概率条，也不表示定位正确概率。": "Lower scores are not displayed as 0–1 probability bars and do not represent probabilities of correct localization.",
  "完整排名与原始精度": "Full ranking and original precision",
  "方案版本": "Scheme version",
  "示例细区证据": "Example fine-region evidence",
  "唯一操作标签": "Operational unique label",
  "歧义允许集合": "Ambiguous allowed set",
  "允许细区": "Allowed regions",
  "该标签来自保存注释，不由模型预测推导。": "Labels come from the saved annotation, not from the model prediction.",
  "将表达谱与冻结参考模型对照，探索粗粒度脑区排序及完整模型分数。": "Compare one expression profile with frozen references. Explore Network candidates and, where supported, independent Group and Exact rankings.",
  "猕猴 · 10 个支持脑区": "10 Networks · Group / Exact",
  "完整三层输入": "Complete three-tier input",
  "第一层面板输入": "Network panel input",
  "下载未完成，请重试。": "Download failed. Please try again."
});

const diagnosticTranslations = {
  'Prepared macaque input must be at most 8 MiB.':'猕猴准备输入不得超过 8 MiB。',
  'Prepared NPZ exceeds the single-sample size limit.':'NPZ 内容超过单样本大小限制。',
  'NPZ needs observed_logcpm, observed, genes, samples and full_library_counts.':'NPZ 需包含 observed_logcpm、observed、genes、samples 和 full_library_counts。',
  'NPZ gene axis must match the supplied 5,000-gene template exactly.':'NPZ 基因轴必须与提供的 5,000 基因模板完全一致。',
  'Exactly one sample is supported.':'每次仅支持一个样本。',
  'CSV needs 5,000 rows and gene_id, ln1p_cpm, observed, full_library_counts columns.':'CSV 需包含 5,000 行及 gene_id、ln1p_cpm、observed、full_library_counts 四列。',
  'CSV gene IDs must be unique and match the frozen panel.':'CSV 基因 ID 必须唯一，并与冻结面板一致。',
  'observed must be 0 or 1; a measured zero uses observed=1.':'observed 必须为 0 或 1；观测到的零值使用 observed=1。',
  'Use the same full-library count total on every CSV row.':'每一行 CSV 必须使用相同的全库计数总量。',
  'Use a prepared NPZ or CSV file.':'请使用准备好的 NPZ 或 CSV 文件。',
  'Require one floating-point 1×5000 array and a Boolean 5000-element mask.':'需要 1×5000 浮点数组及包含 5000 个元素的 Boolean 掩码。',
  'A positive full-library count total is required.':'必须提供正的全库计数总量。',
  'Observed values must be finite and nonnegative ln(1 + CPM).':'观测值必须为有限、非负的 ln(1 + CPM)。'
};

function t(source, values={}) {
  const size = /^文件须非空且不超过 (\d+) MiB。$/.exec(source || '');
  if(size) { source='文件须非空且不超过 {limit} MiB。'; values={limit:size[1]}; }
  const text = language === 'en' ? (messages[source] ?? source) : source;
  return String(text ?? '').replace(/\{(\w+)\}/g, (match,key) => values[key] ?? match);
}

function setText(selector, source, values={}) {
  localizedText.set(selector,{source,values});
  $(selector).textContent=t(source,values);
}

function translateStatic() {
  document.documentElement.lang=language==='en'?'en':'zh-CN';
  document.title=t('BrainTrace · 单样本科研工作台');
  $$('[data-i18n]').forEach(node=>node.textContent=t(node.dataset.i18n));
  for(const attr of ['aria-label','title','content']) {
    $$(`[data-i18n-${attr}]`).forEach(node=>node.setAttribute(attr,t(node.getAttribute(`data-i18n-${attr}`))));
  }
  $$('[data-language]').forEach(node=>node.value=language);
}

function setLanguage(next) {
  language=next==='zh'?'zh':'en';
  try { localStorage.setItem('braintrace-language',language); } catch {}
  translateStatic();
  localizedText.forEach(({source,values},selector)=>$(selector).textContent=t(source,values));
  populateConfigs(); renderControls(); renderUploadStatus();
  if(state.job)renderJob(state.job);
  else if(state.result)renderResult();
  if(bannerState&&!$('#connection-banner').classList.contains('hidden'))renderBanner();
  if($('#docs-dialog').open&&openDoc)openDocs(openDoc);
}

const localizedDocs = {
  "en": {
    "input": "<section class=\"doc-section\"><h3>Human · CEL / CEL.gz</h3><p>Adult bulk-tissue Human Exon 1.0 ST only, up to 80 MiB. Existing frozen PLM builds 16,295 genes before the 200-feature RAW_FIXED / RANK_FIXED model.</p></section><section class=\"doc-section\"><h3>Macaque · Network / Group / Exact</h3><p>5,000-gene NPZ/CSV runs Network only. Full three-tier NPZ needs x (21668×1 raw ln(1+CPM)), genes, observed (21668 Boolean), samples, full_library_counts and scalar contract_version, mapping_version, normalization, full_count_rows. Full CSV needs all 21,668 unique genes and the same repeated metadata.</p><p>The original Ensembl 91/101 mappings remain supported. PsychENCODE adds a distinct frozen Ensembl91-to-XSAnno mapping and common-annotation contract. The original two mappings use full-library normalization before mapping/panel selection. PsychENCODE instead uses the total of all 26,514 public common-annotation rows; its prepared input additionally requires public_common_annotation_counts_total. Measured zero remains observed; a missing lower input is not imputed as an unmeasured gene. No arbitrary TPM, log2 or panel-only normalization. Raw counts are accepted only for the documented complete 26,514-row PsychENCODE single-profile format.</p><p><a href=\"/api/files/input-guide\">Download complete contract</a> · <a href=\"/resources.html\">Examples, gene axes and mapping files</a></p></section><section class=\"doc-section\"><h3>Local data lifecycle</h3><p>Files go to this computer’s loopback service. Pending files and completed results expire after 30 minutes. Download results to keep them; active tasks continue. Language changes never submit another inference request.</p></section>",
    "model": "<section class=\"doc-section\"><h3>Current frozen scheme</h3><p>floor_clip (5,000 genes, L2 multinomial C=0.1) + original Group / Exact.</p><p>Network Top3 screens candidates. Group uses the maximum Top200 Pearson member score; Exact independently uses 0.25*z(corr50)+0.75*z(corr100) within the same candidate set. 43 exact combinations have references. The six additions reuse completed source-only builds; PsychENCODE common-annotation input adaptation is available with a distinct background definition.</p><p>No head-score multiplication, Group gate, new conditional lower model, automatic fallback or fitting. Scores do not represent calibrated anatomical correctness.</p></section><section class=\"doc-section\"><h3>Evidence limits</h3><p>Network sets 208/350 and unique fine-region sets 40/177 have different denominators; only seven source fine-region labels occur across the unique sets. Existing lower transfer is limited. New conditional lower tiers declined externally and the no-multiplier ablation was overall negative; neither is deployed here.</p><p>Human remains a separate nine-class CEL route, without Group/Exact. Unsupported anatomy, arbitrary assays, cfRNA mixtures and patient diagnosis are outside scope. Local sample agreement does not establish cross-OS, public-hosting or universal exact-localization validity.</p><p><a href=\"/resources.html\">Version, coverage and complete evidence notes</a></p></section>"
  },
  "zh": {
    "input": "<section class=\"doc-section\"><h3>Human · CEL / CEL.gz</h3><p>仅成人 bulk-tissue Human Exon 1.0 ST，最大 80 MiB。原冻结 PLM 生成 16,295 基因轴后应用 200 特征 RAW_FIXED / RANK_FIXED 模型。</p></section><section class=\"doc-section\"><h3>Macaque · Network / Group / Exact</h3><p>5,000 基因 NPZ/CSV 只运行 Network。完整三层 NPZ 须含 x（21668×1 原始 ln(1+CPM)）、genes、observed（21668 Boolean）、samples、full_library_counts 以及标量 contract_version、mapping_version、normalization、full_count_rows。全轴 CSV 须含完整 21,668 个唯一基因并逐行重复相同版本信息。</p><p>保留原有 Ensembl 91/101 映射，并新增独立的 PsychENCODE Ensembl91→XSAnno 映射及共同注释输入契约。原两种映射在映射/面板选择之前按完整文库归一化；PsychENCODE 则使用全部 26,514 行公共共同注释计数总和，预处理输入还须含 public_common_annotation_counts_total。观测零仍为已观测，未提交的下层输入不作为生物学缺测填补。不接受任意 TPM、log2 或仅面板归一化。原始计数仅接受规定的完整 26,514 行 PsychENCODE 单样本格式。</p><p><a href=\"/api/files/input-guide\">下载完整契约</a> · <a href=\"/resources.html\">示例、基因轴及映射文件</a></p></section><section class=\"doc-section\"><h3>本地数据生命周期</h3><p>文件仅发往本机回环服务。待运行文件与完成结果在 30 分钟后过期，请及时下载；正在运行的任务继续。切换语言不会再次提交推断。</p></section>",
    "model": "<section class=\"doc-section\"><h3>当前冻结方案</h3><p>floor_clip (5,000 genes, L2 multinomial C=0.1) + original Group / Exact.</p><p>Network Top3 筛候选；Group 用 Top200 Pearson 成员最高分；Exact 在相同候选集独立用 0.25*z(corr50)+0.75*z(corr100)。已有 43 种精确组合参考，其中新增 6 套复用已完成的来源构建；此界面已接入 PsychENCODE 共同注释输入，并单独标明归一化背景。</p><p>没有第一层分数乘入、Group 门控、新条件下层、自动备用或拟合。分数不表示校准的解剖正确概率。</p></section><section class=\"doc-section\"><h3>证据边界</h3><p>Network 集合 208/350 与细区唯一集合 40/177 分母不同；唯一集合合计只覆盖 7 个来源细区。原下层迁移有限，新条件下层外部下降，去乘数消融整体负面，均未接入当前推断。</p><p>人类仍为独立 9 类 CEL 路线，无 Group/Exact。不支持脑区、任意平台、cfRNA 混合样本及患者诊断不在范围内。本地样本一致性不代表跨 OS、公开部署或普遍精确定位验证。</p><p><a href=\"/resources.html\">版本、覆盖与完整证据说明</a></p></section>"
  }
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
Object.assign(messages, {"PsychENCODE 成年恒河猴 · 26,514 行共同注释原始计数": "PsychENCODE adult rhesus · 26,514 common-annotation count rows", "NPZ / CSV：模型输入；TSV / CSV：PsychENCODE 26,514 行计数 · 最大 8 MiB": "NPZ / CSV: model input; TSV / CSV: 26,514-row PsychENCODE counts · up to 8 MiB", "我确认输入符合所选数据来源：原有完整库模型输入，或成年恒河猴 PsychENCODE 全部共同注释行的原始计数；未以 TPM、log2 或截短面板替代。": "I confirm the documented input source: original full-library model input, or all common-annotation raw-count rows from adult rhesus PsychENCODE; not TPM, log2 or a truncated panel.", "PsychENCODE 可提交全部 26,514 行单样本原始计数；使用共同注释背景归一化，与原始完整测序文库不同。": "PsychENCODE accepts all 26,514 raw-count rows for one profile. Normalization uses the common-annotation background, distinct from the original full sequencing library.", "观测 {observed} / 缺失 {missing} · 共同注释计数总和 {library}": "Observed {observed} / missing {missing} · common-annotation count total {library}", "PsychENCODE 共同注释输入检查通过；分母为全部 26,514 行计数，不是原始未过滤测序文库。": "PsychENCODE common-annotation input validated; the denominator includes all 26,514 count rows, not the original unfiltered sequencing library."});

const state = {species:'human', mode:'live', source:'example', config:'RAW_FIXED', example:'GSE128537', bootstrap:null,
  file:null, upload:null, uploading:false, xhr:null, epoch:0, result:null, resultConfig:null,
  busy:false, job:null, timer:null, submitting:false, retryRequest:null};
const zhLabels = {
  '4009':'额叶皮层', '4132':'颞叶皮层', '4180':'枕叶皮层', '4219':'海马', '4275':'壳核',
  '4391':'丘脑', '4696':'小脑皮层', '9001':'黑质', '9512':'延髓',
  'Cingulate gyrus':'扣带回', 'Frontal (agranular frontal motor areas)':'额叶运动区',
  'Hippocampal formation':'海马结构', 'Lateral Prefrontal Cortex':'外侧前额叶皮层',
  'Occipital/Temporal':'枕叶 / 颞叶', 'Operculum/Insula':'岛盖 / 岛叶',
  'Orbitomedial Prefrontal Cortex (OMPFC)':'眶内侧前额叶皮层',
  'Parietal, and Parieto-occipital region':'顶叶与顶枕区域', 'Subcortical':'皮层下', 'Temporal':'颞叶'
};
const descriptions = {
  RAW_FIXED:'使用冻结来源尺度的表达值。', RANK_FIXED:'使用样本内部基因排序。',
  BOTH:'按预先选定的两套配置分别推断，不事后择优。',
  floor_clip:'当前方案：floor_clip + 原 Group / Exact。', baseline:'冻结来源尺度；不应用 floor / clip。',
  floor_only:'冻结来源尺度 + floor。该保存模型 C = 0.01。', clip_only:'冻结来源尺度 + clip。',
  ALL:'四套完整保存配置；不构成独立验证队列。'
};
const phaseNames = {queued:'检查完成并入队', inference:'开始冻结推断', verifying:'对照原输出', complete:'完成', error:'失败'};
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const show = (selector, visible) => $(selector).classList.toggle('hidden', !visible);
const exampleInfo = () => state.bootstrap?.examples?.find(x=>x.id===state.example);
const exampleId = () => state.species === 'human' ? 'GSM755211' : (exampleInfo()?.sample_id || ({GSE128537:'10_10',GSE179328:'LID_100660',PsychENCODE_AMY:'RMB160L.AMY',PsychENCODE_HIP:'RMB160L.HIP'}[state.example]));
const selectedConfigs = () => state.config === 'BOTH' ? ['RAW_FIXED','RANK_FIXED'] : state.config === 'ALL' ? ['baseline','floor_clip','floor_only','clip_only'] : [state.config];
const regionName = id => language==='zh' ? (zhLabels[id] || englishName(id)) : englishName(id);
const englishName = id => state.bootstrap?.human_labels[id] || id;
const scoreText = score => score > 0 && score < 0.0001 ? score.toExponential(3) : score.toFixed(4);
const bytesText = bytes => bytes >= 1024**2 ? `${(bytes / 1024**2).toFixed(2)} MiB` : `${(bytes / 1024).toFixed(1)} KiB`;

async function api(path, options={}) {
  let response;
  try { response = await fetch(path, {cache:'no-store', ...options, headers:{'X-BrainTrace-Token':state.bootstrap?.session_token || '', ...options.headers}}); }
  catch { throw new Error('无法连接本地服务。请确认启动终端仍在运行，然后重试。'); }
  let payload;
  try { payload = await response.json(); } catch { throw new Error('本地服务返回了无法读取的响应。请检查启动终端。'); }
  if (!response.ok) {
    const error = new Error(payload.error?.message || '请求未完成，请重试。');
    error.code = payload.error?.code; error.detail = payload.error?.detail; throw error;
  }
  return payload;
}

function banner(message, retryLabel, retry, suffix='') {
  bannerState={message,retryLabel,retry,suffix};renderBanner();show('#connection-banner',true);
}

function renderBanner() {
  const {message,retryLabel,retry,suffix}=bannerState;
  const node=$('#connection-banner');node.replaceChildren();
  node.append(document.createTextNode(t(message)+(suffix?' '+t(suffix):'')));
  if(retry){const button=document.createElement('button');button.className='text-button';button.textContent=t(retryLabel);button.addEventListener('click',retry);node.append(button);}
}

function clearResult() {
  state.result=null; state.resultConfig=null;
  show('#result-content',false); show('#result-actions',false); show('#result-mode',false); show('#empty-result',true);
  show('#comparison-banner',false);
  $$('.workflow li').forEach(node=>node.classList.remove('current','done'));
  $('#step-input').classList.add('current');
}

function resetContext({removeFile=true}={}) {
  state.epoch++;
  state.xhr?.abort(); state.xhr=null; state.uploading=false;
  if (removeFile) {
    const oldUpload = state.upload?.upload_id;
    if (oldUpload) api(`/api/uploads/${encodeURIComponent(oldUpload)}`,{method:'DELETE'}).catch(()=>{});
    state.file=null; state.upload=null; uploadView=null; $('#file-input').value=''; $('#contract').checked=false;
    $('#upload-status').textContent=''; $('#upload-status').className='upload-status'; show('#file-review',false);
  }
  state.job=null; state.retryRequest=null;
  sessionStorage.removeItem('braintrace-job');
  clearTimeout(state.timer); clearResult(); show('#job-panel',false); show('#connection-banner',false);
}

function renderControls() {
  document.body.classList.toggle('saved-mode',state.mode==='saved');
  const human = state.species==='human';
  $$('[data-species]').forEach(node=>{
    const active=node.dataset.species===state.species;node.classList.toggle('active',active);node.setAttribute('aria-pressed',active);node.disabled=state.busy;
  });
  $$('[data-mode]').forEach(node=>{
    const active=node.dataset.mode===state.mode;node.classList.toggle('active',active);node.setAttribute('aria-pressed',active);node.disabled=state.busy;
  });
  $$('[data-source]').forEach(node=>{
    const active=node.dataset.source===state.source;node.classList.toggle('active',active);node.setAttribute('aria-pressed',active);node.disabled=state.busy;
  });
  $('#configuration').disabled=state.busy;
  $('#configuration').value=state.config;
  setText('#config-description',descriptions[state.config]);
  $('#region-count').textContent=human?'09':'10'; $('#feature-count').textContent=human?'200':'5,000';
  $('#example-title').textContent=human?'GSM755211.CEL.gz':`${state.example} · ${exampleId()}`;
  show('#macaque-example-choice',!human&&(state.source==='example'||state.mode==='saved'));$('#example-choice').value=state.example;$('#example-choice').disabled=state.busy;
  $('#example-ext').textContent=human?'CEL':state.example.startsWith('PsychENCODE')?'TSV':'NPZ';
  setText('#example-subtitle',human?'Human Exon 1.0 ST · bulk tissue · GSM755211':state.example.startsWith('PsychENCODE')?'PsychENCODE 成年恒河猴 · 26,514 行共同注释原始计数':'三层示例 · 完整 21,668 基因轴');
  $('#example-download').href=human?'/api/files/human-example':exampleInfo()?.download_key?'/api/files/'+exampleInfo().download_key:state.example==='GSE179328'?'/api/files/macaque-second-example':'/api/files/macaque-example';
  $('#file-input').accept=human?'.cel,.CEL,.cel.gz,.CEL.gz':'.npz,.csv,.tsv';
  setText('#upload-format',human?'CEL / CEL.gz · 单个文件 · 最大 80 MiB':'NPZ / CSV：模型输入；TSV / CSV：PsychENCODE 26,514 行计数 · 最大 8 MiB');
  setText('#contract-text',human?'我确认这是符合规范的成人 bulk-tissue Human Exon 1.0 ST CEL 样本。':'我确认输入符合所选数据来源：原有完整库模型输入，或成年恒河猴 PsychENCODE 全部共同注释行的原始计数；未以 TPM、log2 或截短面板替代。');
  $('#contract-summary').innerHTML=human
    ? t("<div class=\"contract-platform\">Human Exon 1.0 ST<br>成人 bulk-tissue CEL</div><div class=\"contract-formats\"><span class=\"format-tag\">.CEL</span><span class=\"format-tag\">.CEL.gz</span><span class=\"format-tag\">≤ 80 MiB</span></div><ul class=\"contract-bullets\"><li>冻结 PLM 生成完整 16,295 基因轴，再应用保存的 200 特征模型。</li><li>文件名不能证明平台、成人资格或解剖身份。</li><li>不接收任意表达矩阵、TPM 或其他芯片平台。</li></ul>")
    : `<div class="contract-platform">Macaque · Network / Group / Exact</div><div class="contract-formats"><span class="format-tag">.NPZ</span><span class="format-tag">.CSV</span><span class="format-tag">.TSV</span><span class="format-tag">≤ 8 MiB</span></div><p>${t('三层输入需要完整 21,668 基因轴及版本信息。5,000 基因输入只运行 Network。')}</p><p>${t('PsychENCODE 可提交全部 26,514 行单样本原始计数；使用共同注释背景归一化，与原始完整测序文库不同。')}</p><p>${t('Group 与 Exact 在同一个 Top3 Network 候选全集中独立排名；第一层分数不乘入下层。')}</p>`;
  const ready=state.bootstrap?.runtime[state.species];
  setText('#runtime-badge',!state.bootstrap?'连接本地服务…':ready?'●  冻结环境可用':'环境未就绪');
  $('#runtime-badge').className=`badge ${ready?'green':'neutral'}`;
  show('#live-controls',state.mode==='live');show('#saved-notice',state.mode==='saved');
  show('#example-card',state.source==='example');show('#upload-controls',state.source==='upload');
  ['#sample-id','#file-input','#contract','#remove-file','#nav-examples','#empty-example'].forEach(selector=>$(selector).disabled=state.busy);
  updateRunButton();
}

function populateConfigs() {
  const options=state.species==='human'?[['RAW_FIXED','RAW_FIXED · 来源尺度'],['RANK_FIXED','RANK_FIXED · 样本排序'],['BOTH','RAW + RANK · 两套配置']]
    :[['floor_clip','floor_clip + Group / Exact']];
  $('#configuration').replaceChildren(...options.map(([value,label])=>new Option(t(label),value)));
}

function updateRunButton() {
  const ready=state.bootstrap?.runtime[state.species];
  const inputReady=state.source==='example'||(state.upload && $('#contract').checked && !state.uploading);
  $('#run-button').disabled=!ready||!inputReady||state.busy;
  $('#run-button').innerHTML=`${t(state.busy?'推断处理中':'运行冻结推断')} <span aria-hidden="true">${state.busy?'⋯':'→'}</span>`;
  setText('#run-hint',state.busy?'输入与配置已锁定。完成后可切换或开始新任务。':!state.bootstrap?'正在连接本地服务…':!ready?'运行环境未就绪；可先查看保存示例。':state.source==='example'?'运行真实单样本，并自动对照原保存输出。':state.uploading?'文件正在上传与校验，请稍候。':!state.upload?'选择一个符合规范的文件，先完成结构检查。':!$('#contract').checked?'文件检查完成，请确认样本与预处理符合规范。':'输入已就绪。将使用当前预先选择的冻结配置。');
}

function switchSpecies(species) {
  if(state.busy||species===state.species)return;
  resetContext();state.species=species;state.config=species==='human'?'RAW_FIXED':'floor_clip';
  populateConfigs();renderControls();if(state.mode==='saved')loadSaved();
}

function switchMode(mode) {
  if(state.busy)return;
  resetContext();state.mode=mode;renderControls();if(mode==='saved')loadSaved();
}

async function loadSaved() {
  const epoch=state.epoch;
  setText('#empty-result h3','正在读取保存输出…');
  try {
    const result=await api(`/api/examples?${new URLSearchParams({species:state.species,configurations:selectedConfigs().join(','),example_id:state.example})}`);
    if(epoch!==state.epoch||state.mode!=='saved')return;
    state.result=result;renderResult();
  } catch(error) { if(epoch===state.epoch)banner(error.message,'重试读取',loadSaved); }
  finally { setText('#empty-result h3','下一个线索，从这里开始'); }
}

async function selectFile(file) {
  if(state.busy)return;
  resetContext();state.file=file;renderControls();
  if(!file)return;
  $('#file-name').textContent=file.name;$('#file-size').textContent=bytesText(file.size);show('#file-review',true);
  const human=state.species==='human';const allowed=human?/\.cel(?:\.gz)?$/i:/\.(npz|csv|tsv)$/i;
  if(!allowed.test(file.name))return uploadError(human?'仅接受 .CEL 或 .CEL.gz；普通 .gz 文件不符合规范。':'接受原有 .NPZ/.CSV，或 PsychENCODE 单样本计数 .TSV/.CSV。');
  if(!file.size||file.size>(human?80:8)*1024**2)return uploadError(`文件须非空且不超过 ${human?80:8} MiB。`);
  validateFile();
}

function uploadError(message,detail) {
  state.upload=null;state.uploading=false;uploadView={kind:'invalid',message,detail};renderUploadStatus();updateRunButton();
}

function renderUploadStatus() {
  const node=$('#upload-status');node.replaceChildren();node.className='upload-status';
  if(!uploadView)return;
  if(uploadView.kind==='invalid'){
    node.classList.add('invalid');node.textContent=t(uploadView.message);
    if(uploadView.detail){const line=document.createElement('div');line.textContent=language==='zh'?(diagnosticTranslations[uploadView.detail]||'原始校验信息（英文）：'+uploadView.detail):uploadView.detail;node.append(line);}
  } else if(uploadView.kind==='valid') {
    const summary=state.upload.summary;node.classList.add('valid');node.textContent='✓ '+t(summary.message);
    if(summary.observed_features!==undefined){
      const details=document.createElement('div');details.textContent=t(summary.normalization_background==='public_common_annotation_26514'?'观测 {observed} / 缺失 {missing} · 共同注释计数总和 {library}':'观测 {observed} / 缺失 {missing} · 全库计数 {library}',{observed:summary.observed_features.toLocaleString(language),missing:summary.missing_features.toLocaleString(language),library:summary.full_library_counts.toLocaleString(language)});node.append(details);
    }
    if(summary.lower_input_status){const line=document.createElement('div');line.textContent=t('下层输入状态')+': '+lowerStatus(summary.lower_input_status)+(summary.lower_missing_fields.length?' · '+t('需提供')+': '+summary.lower_missing_fields.join(', '):'');node.append(line);}
  } else {
    node.textContent=t(uploadView.message);
    if(uploadView.kind==='progress'){
      const progress=document.createElement('progress');progress.max=100;progress.value=uploadView.progress;progress.setAttribute('aria-label',t('文件上传进度'));node.append(progress);
    }
  }
}

function validateFile() {
  if(!state.file||state.busy)return;
  const sampleId=$('#sample-id').value;
  if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(sampleId))return uploadError('请先填写有效的样本 ID，以字母或数字开头。');
  const oldId=state.upload?.upload_id;if(oldId)api(`/api/uploads/${encodeURIComponent(oldId)}`,{method:'DELETE'}).catch(()=>{});
  state.xhr?.abort();state.epoch++;const epoch=state.epoch;state.upload=null;state.uploading=true;
  clearResult();show('#job-panel',false);state.retryRequest=null;sessionStorage.removeItem('braintrace-job');
  uploadView={kind:'progress',progress:0,message:'正在上传到本地推断服务…'};renderUploadStatus();
  const xhr=new XMLHttpRequest();state.xhr=xhr;
  xhr.open('POST',`/api/uploads?${new URLSearchParams({species:state.species,sample_id:sampleId,filename:state.file.name})}`);
  xhr.setRequestHeader('X-BrainTrace-Token',state.bootstrap.session_token);xhr.setRequestHeader('Content-Type','application/octet-stream');xhr.timeout=90000;
  xhr.upload.onprogress=event=>{
    if(epoch!==state.epoch)return;
    if(event.lengthComputable)uploadView.progress=100*event.loaded/event.total;
    if(event.loaded===event.total)uploadView.message='上传完成，正在校验结构…';
    renderUploadStatus();
  };
  xhr.onload=()=>{
    let payload;try{payload=JSON.parse(xhr.responseText);}catch{if(epoch===state.epoch)uploadError('本地校验响应无效，请重新选择文件。');return;}
    if(epoch!==state.epoch){if(payload.upload_id)api(`/api/uploads/${encodeURIComponent(payload.upload_id)}`,{method:'DELETE'}).catch(()=>{});return;}
    state.uploading=false;state.xhr=null;
    if(xhr.status<200||xhr.status>=300)return uploadError(payload.error?.message||'校验失败，请检查输入。',payload.error?.detail);
    state.upload=payload;uploadView={kind:'valid'};renderUploadStatus();
    updateRunButton();
  };
  xhr.onerror=()=>{if(epoch===state.epoch)uploadError('上传连接中断，请重新选择文件。');};
  xhr.ontimeout=()=>{if(epoch===state.epoch)uploadError('上传或校验超时，请重新选择文件。');};
  xhr.send(state.file);updateRunButton();
}

async function startRun() {
  if(state.busy)return;
  const payload=state.retryRequest || {species:state.species,configurations:selectedConfigs(),source:state.source,example_id:state.example,
    sample_id:state.source==='example'?exampleId():$('#sample-id').value,upload_id:state.upload?.upload_id,
    contract_confirmed:$('#contract').checked,request_key:crypto.randomUUID()};
  state.busy=true;state.submitting=true;state.job=null;clearResult();show('#connection-banner',false);renderControls();
  show('#job-panel',true);setText('#job-heading','正在提交本机任务');setText('#job-detail','等待服务确认，尚未报告推断完成。');
  $('#job-spinner').className='spinner';$('#job-elapsed').textContent='00:00';$('#job-events').replaceChildren();show('#job-error',false);
  try {
    const job=await api('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    state.retryRequest=null;state.submitting=false;state.job=job;
    sessionStorage.setItem('braintrace-job',job.id);renderJob(job);pollJob(job.id);
  } catch(error) {
    state.busy=false;state.submitting=false;state.retryRequest=error.code?null:payload;
    $('#job-spinner').className='spinner failed';setText('#job-heading',error.code?'任务未提交':'任务提交状态未确认');
    setText('#job-detail',error.code?'没有启动新的推断。修正输入后可重试。':'重试时将使用同一个请求标识，避免重复推断。');
    setText('#job-error',error.message);show('#job-error',true);renderControls();
  }
}

function renderJob(job) {
  state.job=job;show('#job-panel',true);
  const active=job.status==='queued'||job.status==='running';state.busy=active;renderControls();
  setText('#job-heading',job.status==='queued'?t('任务已排队')+(job.queue_position?t(' · 前方 {count} 个任务',{count:job.queue_position}):''):job.status==='running'?'正在运行冻结模型':job.status==='succeeded'?'单样本推断完成':'本次推断未完成');
  setText('#job-detail',`${job.sample_id} · ${job.configurations.join(' / ')} · ${t(active?'仅显示服务端实际阶段，不估算完成百分比。':'真实任务记录')}`);
  $('#job-spinner').className=`spinner${active?'':job.status==='failed'?' failed':' stopped'}`;
  const seconds=Math.floor(job.elapsed_seconds);$('#job-elapsed').textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
  $('#job-events').replaceChildren(...job.events.map(event=>{
    const span=document.createElement('span');span.textContent=`${t(phaseNames[event.phase])} · ${new Date(event.at).toLocaleTimeString(language==='en'?'en-US':'zh-CN',{hour12:false})}`;span.title=t(event.message);return span;
  }));
  $('#step-input').classList.remove('current');$('#step-input').classList.add('done');$('#step-run').classList.toggle('current',active);
  show('#job-error',job.status==='failed');if(job.error)setText('#job-error',job.error.message);
  if(job.status==='succeeded'){
    state.result=job.result;renderResult();
  }
}

async function pollJob(id) {
  clearTimeout(state.timer);
  try {
    const job=await api(`/api/jobs/${encodeURIComponent(id)}`);
    if(state.job?.id!==id)return;
    show('#connection-banner',false);renderJob(job);
    if(job.status==='queued'||job.status==='running')state.timer=setTimeout(()=>pollJob(id),900);
  } catch(error) {
    if(state.job?.id!==id)return;
    if(error.code==='job_expired'){
      state.busy=false;state.job=null;renderControls();sessionStorage.removeItem('braintrace-job');
      $('#job-spinner').className='spinner failed';setText('#job-heading','任务已过期或服务已重启');
      setText('#job-detail','结果未保留在当前服务内。可重新提交样本。');banner(error.message);return;
    }
    banner(error.message,'重新连接',()=>pollJob(id),'当前任务可能仍在执行。');
    state.timer=setTimeout(()=>pollJob(id),4000);
  }
}

function renderResult() {
  const result=state.result;if(!result)return;
  const live=result.mode==='live_frozen_inference';
  show('#empty-result',false);show('#result-content',true);show('#result-actions',true);show('#result-mode',true);
  setText('#result-mode',live?'本次真实推断':'原保存输出 · 未执行推断');$('#result-mode').className=`badge ${live?'green':'neutral'}`;
  $('#result-meta').innerHTML=`<span>${t('样本')} <strong>${escapeHtml(result.sample_id)}</strong></span><span>${t(result.species==='human'?'Human · 9 类':'Macaque · 10 类')}</span><span>${t('{count} 套预先选择配置',{count:Object.keys(result.predictions).length})}</span>${result.observed_features!==undefined?`<span>${t('观测 {observed} / 缺失 {missing}',{observed:result.observed_features.toLocaleString(language),missing:result.missing_features.toLocaleString(language)})}</span>`:''}`;
  const comparison=result.saved_output_comparison;show('#comparison-banner',Boolean(comparison));
  if(comparison){
    const differences=Object.values(comparison.configurations).flatMap(x=>[x.max_score_difference,x.max_decision_difference]).filter(x=>x!==null);
    $('#comparison-banner').className=`notice ${comparison.pass?'success':'error'}`;
    $('#comparison-banner').textContent=comparison.pass?t('✓ 与原保存示例一致：类别轴与排序相同，最大数值差 {difference}（atol = {tolerance}，rtol = 0）。仅说明该示例本次推断一致。',{difference:Math.max(...differences),tolerance:comparison.absolute_tolerance}):t('本次结果与原保存示例存在差异。保留下方真实输出，不报告为成功复现；请查看 JSON 中的逐配置比较。');
  }
  const keys=Object.keys(result.predictions);if(!keys.includes(state.resultConfig))state.resultConfig=keys[0];
  $('#result-config-tabs').replaceChildren(...keys.map((key,index)=>{
    const button=document.createElement('button');button.textContent=key;button.id=`result-tab-${index}`;button.setAttribute('role','tab');button.setAttribute('aria-controls','prediction-panel');
    const selected=key===state.resultConfig;button.setAttribute('aria-selected',selected);button.tabIndex=selected?0:-1;button.classList.toggle('active',selected);
    button.addEventListener('click',()=>{state.resultConfig=key;renderResult();$(`#result-tab-${index}`).focus();});
    button.addEventListener('keydown',event=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(event.key)){event.preventDefault();const target=event.key==='Home'?0:event.key==='End'?keys.length-1:(index+(event.key==='ArrowRight'?1:-1)+keys.length)%keys.length;state.resultConfig=keys[target];renderResult();$(`#result-tab-${target}`).focus();}});
    return button;
  }));
  $('#prediction-panel').setAttribute('aria-labelledby',`result-tab-${keys.indexOf(state.resultConfig)}`);
  const item=result.predictions[state.resultConfig];const byClass=Object.fromEntries(item.classes.map((key,i)=>[key,{score:item.scores[i],decision:item.decision?.[i]}]));
  $('#candidate-cards').innerHTML=item.ranking.slice(0,3).map((id,index)=>`<article class="candidate-card ${index===0?'top':''}"><div class="candidate-topline"><span>${t('候选')} ${String(index+1).padStart(2,'0')}</span><strong>${index===0?'↗':'·'}</strong></div><h3>${escapeHtml(regionName(id))}</h3><div class="region-english">${language==='zh'?escapeHtml(englishName(id)):''}</div><div class="candidate-score"><strong>${scoreText(byClass[id].score)}</strong><span>${t('模型分数')}</span></div></article>`).join('');
  setText('#score-count','{count} 个支持类别',{count:item.classes.length});
  $('#score-chart').innerHTML=item.ranking.map((id,index)=>`<div class="score-row"><span class="score-rank">${String(index+1).padStart(2,'0')}</span><span class="score-label ${index===0?'first':''}" title="${escapeHtml(englishName(id))}">${escapeHtml(regionName(id))}</span><div class="score-track" aria-hidden="true"><div class="score-bar" style="width:${Math.max(0,Math.min(1,byClass[id].score))*100}%"></div></div><span class="score-value" title="${byClass[id].score}">${scoreText(byClass[id].score)}</span></div>`).join('');
  const context=[['结果来源',live?'本次冻结推断':'已有示例输出'],['冻结配置',state.resultConfig],['新增拟合',String(result.new_fits)],['模型分数','仅用于候选排序']];
  if(result.observed_features!==undefined)context.push(['缺失特征处理','冻结来源均值']);
  $('#result-context').innerHTML=context.map(([label,value])=>`<div class="context-item"><span>${escapeHtml(t(label))}</span><strong>${escapeHtml(t(value))}</strong></div>`).join('');
  if(result.reference_labels){
    const hit1=result.reference_labels.includes(item.ranking[0]);const hit3=item.ranking.slice(0,3).some(x=>result.reference_labels.includes(x));
    $('#reference-evidence').innerHTML=`<div class="truth-card"><strong>${t('示例参考标签 · 不由预测分数推导')}</strong>${result.reference_labels.map(x=>escapeHtml(regionName(x))).join(' / ')}<div class="truth-status"><span>Top 1 ${t(hit1?'命中':'未命中')}</span><span>Top 3 ${t(hit3?'包含':'未包含')}</span></div></div>`;
  } else $('#reference-evidence').innerHTML=`<p>${t('此处不从模型最高分推导样本真实解剖标签，也不据此报告定位正确率。')}</p>`;
  $('#score-table-head').innerHTML=`<tr><th>${t('排序')}</th><th>${t('候选脑区')}</th><th>${t('类别 ID / 原标签')}</th><th>${t('模型分数')}</th>${item.decision?`<th>${t('决策值')}</th>`:''}</tr>`;
  $('#score-table-body').innerHTML=item.ranking.map((id,index)=>`<tr><td>${index+1}</td><td>${escapeHtml(regionName(id))}</td><td>${escapeHtml(id)}</td><td>${byClass[id].score}</td>${item.decision?`<td>${byClass[id].decision}</td>`:''}</tr>`).join('');
  renderLowerTiers(result);
  $('#raw-json').textContent=JSON.stringify(result,null,2);
  $$('.workflow li').forEach(node=>node.classList.remove('current'));$('#step-input').classList.add('done');
  $('#step-run').classList.toggle('done',live);$('#step-result').classList.add('current');
}

async function download(kind) {
  const result=state.result;if(!result)return;
  let text,type;
  if(kind==='json'){text=JSON.stringify(result,null,2)+'\n';type='application/json';}
  else {
    const path=result.mode==='live_frozen_inference'?`/api/jobs/${encodeURIComponent(state.job.id)}/scores.csv`:`/api/examples?${new URLSearchParams({species:result.species,configurations:Object.keys(result.predictions).join(','),example_id:state.example,format:'csv'})}`;
    try {const response=await fetch(path);if(!response.ok)throw new Error();text=await response.text();type='text/csv;charset=utf-8';}
    catch {banner('下载未完成，请重试。');return;}
  }
  const url=URL.createObjectURL(new Blob([text],{type}));const anchor=document.createElement('a');
  anchor.href=url;anchor.download=`braintrace_${result.species}_${result.sample_id}_${result.mode}.${kind}`;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}


function lowerStatus(status){return t({compatible:'完整三层输入',succeeded:'已完成',input_insufficient:'下层未运行：输入不足',input_incompatible:'下层未运行：输入不兼容',reference_unavailable:'下层未运行：该候选组合的参考尚未提供',failed:'下层运行失败',not_evaluable:'下层不可评价：有效信号不足'}[status]||status);}
function renderLowerTiers(result){
  const has=Boolean(result.tiers);show('#lower-tier-results',has);show('#network-heading',has);if(!has)return;
  $('#network-heading').textContent='Network · '+t('候选筛选');
  const e=escapeHtml;const context=result.example_context;
  let html=`<div class="lower-intro"><h3>${t('独立下层排序')}</h3><p>${t('Group 与 Exact 在同一个 Top3 Network 候选全集中独立排名；第一层分数不乘入下层。')}</p><small>${t('方案版本')}: ${e(result.scheme_id)} · ${e(result.reference_id||'—')}</small></div>`;
  for(const tier of ['Group','Exact']){
    const item=result.tiers[tier];const group=tier==='Group';const valid=item.status==='succeeded';
    const label=t(group?'Pearson 相关系数（Top200 成员最高分）':'融合分数（0.25 × z50 + 0.75 × z100）');
    html+=`<section class="panel lower-panel"><div class="scores-heading"><h3>${tier}</h3><span class="badge ${valid?'green':'neutral'}">${lowerStatus(item.status)}</span></div>`;
    if(valid){
      const row=(id,rank)=>{const i=item.classes.indexOf(id);return `<tr><td>${rank+1}</td><td class="lower-id">${e(id)}</td><td title="${item.scores[i]}">${item.scores[i]}</td>${group?`<td>${item.member_counts[i]}</td><td>${item.members[i].map(e).join(' · ')}</td>`:''}</tr>`;};
      const table=ranking=>`<div class="table-scroll"><table><thead><tr><th>${t('排序')}</th><th>${t('原类别 ID')}</th><th>${label}</th>${group?`<th>${t('成员数')}</th><th>${t('成员细区')}</th>`:''}</tr></thead><tbody>${ranking.map(row).join('')}</tbody></table></div>`;
      html+=table(item.ranking.slice(0,3))+`<details class="raw-detail"><summary>${t('完整排名与原始精度')} (${item.ranking.length})</summary>${table(item.ranking)}</details>`;
    }else html+=`<p>${lowerStatus(item.status)}</p>${item.missing_fields?.length?`<p>${t('需提供')}: <code>${item.missing_fields.map(e).join(', ')}</code></p>`:''}${item.reason&&item.status==='not_evaluable'?`<code>${e(item.reason)}</code>`:''}`;
    html+=`</section>`;
  }
  html+=`<p class="chart-note">${t('下层分数不使用 0–1 概率条，也不表示定位正确概率。')}</p>`;
  if(result.input_summary?.normalization_background==='public_common_annotation_26514'){
    html+=`<div class="notice info"><strong>PsychENCODE · ${language==='zh'?'共同注释背景':'Common-annotation background'}</strong><p>${language==='zh'?'分母为全部 26,514 行公共计数，不是原始未过滤文库。':'The denominator includes all 26,514 public count rows, not the original unfiltered library.'} ${e(result.input_summary.public_common_annotation_counts_total)}</p></div>`;
  }
  if(context){const kind=['primary_unique','unique_operational'].includes(context.fine_endpoint)?t('唯一操作标签'):context.fine_endpoint==='parent_compatible'?(language==='zh'?'父结构兼容（非细区定位）':'Parent compatibility (not subregion localization)'):t('歧义允许集合');html+=`<div class="notice info"><strong>${t('示例细区证据')} · ${kind}</strong><p>${t('允许细区')}: ${context.allowed_regions.map(e).join(' · ')}</p><p>${t('该标签来自保存注释，不由模型预测推导。')}</p><p lang="en">${e(context.reason)}</p></div>`;}
  $('#lower-tier-results').innerHTML=html;
}

function openDocs(kind) {
  openDoc=kind;
  setText('#docs-title',kind==='input'?'输入规范与示例文件':'模型与证据边界');
  $('#docs-content').innerHTML=localizedDocs[language][kind];
  const section=document.createElement('section');section.className='doc-section';
  const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent=t('查看随 demo 保留的原始说明（英文原文）');
  const pre=document.createElement('pre');pre.lang='en';pre.textContent=kind==='input'?state.bootstrap?.input_formats:state.bootstrap?.model_card;
  details.append(summary,pre);section.append(details);$('#docs-content').append(section);if(!$('#docs-dialog').open)$('#docs-dialog').showModal();
}

$$('[data-language]').forEach(node=>node.addEventListener('change',()=>setLanguage(node.value)));
$$('[data-species]').forEach(node=>node.addEventListener('click',()=>switchSpecies(node.dataset.species)));
$$('[data-mode]').forEach(node=>node.addEventListener('click',()=>switchMode(node.dataset.mode)));
$$('[data-source]').forEach(node=>node.addEventListener('click',()=>{if(state.busy)return;resetContext();state.source=node.dataset.source;renderControls();}));
$('#example-choice').addEventListener('change',()=>{if(state.busy)return;const value=$('#example-choice').value;resetContext();state.example=value;renderControls();if(state.mode==='saved')loadSaved();});
$('#configuration').addEventListener('change',()=>{if(state.busy)return;const config=$('#configuration').value;resetContext({removeFile:false});state.config=config;renderControls();if(state.mode==='saved')loadSaved();else if(state.file&&!state.upload)validateFile();});
$('#file-input').addEventListener('change',event=>selectFile(event.target.files[0]));
$('#remove-file').addEventListener('click',()=>selectFile(null));
$('#contract').addEventListener('change',updateRunButton);
let sampleTimer;
$('#sample-id').addEventListener('input',()=>{
  state.xhr?.abort();state.epoch++;state.uploading=false;
  const oldId=state.upload?.upload_id;if(oldId)api(`/api/uploads/${encodeURIComponent(oldId)}`,{method:'DELETE'}).catch(()=>{});
  state.upload=null;state.retryRequest=null;$('#contract').checked=false;clearResult();show('#job-panel',false);updateRunButton();
  uploadView=state.file?{kind:'waiting',message:'样本 ID 已更改，等待重新校验…'}:null;renderUploadStatus();
  clearTimeout(sampleTimer);sampleTimer=setTimeout(validateFile,500);
});
['dragenter','dragover'].forEach(type=>$('#dropzone').addEventListener(type,event=>{event.preventDefault();if(!state.busy)$('#dropzone').classList.add('dragover');}));
['dragleave','drop'].forEach(type=>$('#dropzone').addEventListener(type,event=>{event.preventDefault();$('#dropzone').classList.remove('dragover');}));
$('#dropzone').addEventListener('drop',event=>{if(state.busy)return;if(event.dataTransfer.files.length!==1){resetContext();renderControls();uploadError('每次仅支持一个样本文件，请重新选择。');return;}selectFile(event.dataTransfer.files[0]);});
$('#run-button').addEventListener('click',startRun);
$('#nav-examples').addEventListener('click',()=>switchMode('saved'));
$('#empty-example').addEventListener('click',()=>switchMode('saved'));
$('#download-json').addEventListener('click',()=>download('json'));$('#download-csv').addEventListener('click',()=>download('csv'));
$$('[data-doc]').forEach(node=>node.addEventListener('click',()=>openDocs(node.dataset.doc)));
$('#close-docs').addEventListener('click',()=>$('#docs-dialog').close());
$('#docs-dialog').addEventListener('click',event=>{if(event.target===$('#docs-dialog')){const rect=event.target.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)event.target.close();}});

async function initialize() {
  translateStatic();populateConfigs();renderControls();
  try {
    state.bootstrap=await api('/api/bootstrap');renderControls();if(state.result)renderResult();show('#connection-banner',false);
    const previous=sessionStorage.getItem('braintrace-job');
    if(previous){
      try {
        const job=await api(`/api/jobs/${encodeURIComponent(previous)}`);
        state.species=job.species;state.mode='live';state.source=job.source;state.example=job.example_id||'GSE128537';
        state.config=job.configurations.length===2&&job.species==='human'?'BOTH':job.configurations.length===4?'ALL':job.configurations[0];
        $('#sample-id').value=job.sample_id;populateConfigs();state.job=job;renderJob(job);
        if(job.status==='queued'||job.status==='running')pollJob(job.id);
      } catch(error){sessionStorage.removeItem('braintrace-job');banner(error.message);}
    }
  } catch(error){banner(error.message,'重新连接',initialize);}
}
initialize();
