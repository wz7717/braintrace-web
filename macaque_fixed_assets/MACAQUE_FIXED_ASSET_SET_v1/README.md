# BrainTrace MACAQUE_FIXED_ASSET_SET_v1

本集合按原字节提供96件核心固定资产及2件原合同，共98件、13,900,180 B。逐件相对路径、继承bytes／SHA、贡献分层及43参考ID见 [SOURCE_AND_NOTICE_MANIFEST.json](SOURCE_AND_NOTICE_MANIFEST.json)。

| 文件组 | 件数 | 范围 |
|---|---:|---|
| C06当前固定Network | 4 | floor_clip模型、scaler、state及5000-feature轴 |
| C09共享support | 4 | lower轴、all819 raw mean、BEAMS及REGION_PARENT |
| C09参考对 | 86 | beam_001至beam_043，各INPUT及RULES一对 |
| PsychENCODE固定件 | 2 | 原Ensembl91／XSAnno strict mapping及26514-row公共ID轴 |
| 原合同 | 2 | metadata/SCHEME.json及docs/PSYCHENCODE_INPUT.md |

43套为原37套加已完成的source-only 6套。六套由原源数据构建，不来自PsychENCODE外部表达或truth。raw mean是lower层的未加权all819源raw ln(1+CPM)均值，不是Network scaler。PsychENCODE的26514-row common-annotation背景不同于21668维lower轴及5000-feature Network面板，不能改称原始完整测序库。原合同位于[输入说明](assets/docs/PSYCHENCODE_INPUT.md)。

## 许可与原权利

仅王震有权许可的项目贡献采用 [CC BY-NC 4.0](notices/CC-BY-NC-4.0.txt)，详见 [项目贡献条款](notices/PROJECT_CONTRIBUTION_TERMS.txt)。不是将98件全字节统一CC化。合规非商业复制、修改和再分享依标准CC条款进行；纯事实ID、公有领域、无排他权数值及法律例外不新增限制。第三方内容和实际适用的原提供条件保持原义。

请分别阅读 [第三方说明](notices/THIRD_PARTY_NOTICES.md)、[Bo与NCBI来源](notices/BO_SOURCE_SCOPE_AND_NCBI_POLICY.md)、[Ensembl](notices/ENSEMBL_DATA_TERMS_AND_ATTRIBUTION.md)、[XSAnno](notices/XSANNO_SOURCE_AND_TERMS.md)及 [PsychENCODE来源局限](notices/PSYCHENCODE_SOURCE_LIMITS.md)。混合mapping不统一标为GPL或CC。

## 使用、引用与边界

保存时保持`assets/`以下science／metadata／docs布局；引用本集合名、公开manifest及实际托管页面提供的固定commit，并保留原notice和创作者／来源归属。原件字节保留只描述这次提供，合法下游改编可以另名或换格式，须标明改动，不能冒充未改冻结件。

原RULES保留成员、注释、训练定位／身份和历史路径等metadata，不宣称没有Bo派生字段。原合同中的历史部署状态和命令引用应结合本说明阅读；被引用代码或数据不因此随包。43组合不等于120组合全覆盖，未知组合的原reference_unavailable行为保持。

本集合不含三份Bo精确处理源、C07历史模型、两GEO映射、完整PsychENCODE count／BrainInfo／原注释、演示或77-profile输出、实现代码、库或环境。它不是独立可运行环境或完整论文复现包。人类资产和独立源码许可不扩展到本集合；本集合也不扩大它们的范围。
