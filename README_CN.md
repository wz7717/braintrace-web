# BrainTrace 网页源码仓库

仓库：https://github.com/wz7717/braintrace-web ，初建为私有。这里只保存网页源码和说明；runtime_assets 是服务器运行资产，不加入仓库。
两者通过 tools/prepare_runtime.py 复制组装为全新应用目录，既有源码、资产和旧包不覆盖。

```text
python -X utf8 -B tools/prepare_runtime.py --assets ../runtime_assets --out ../assembled_runtime
cd ../assembled_runtime
python -X utf8 -B site_server.py --port 8766
```

先使用固定 Python 3.11.9 环境；完整步骤见 docs/DEPLOYMENT_CN.md。
上面第一条只复制文件，第二条启动页面，不运行科学推断。网页选“保存结果”时复用原输出。

原 37 套参考与模型保持原文件，另复用成年队列已完成的 6 套，当前服务器资产共 43 套。
保留原有两种输入映射，并新增独立的 PsychENCODE common-annotation 适配；见 docs/PSYCHENCODE_INPUT.md。
当前方案并不覆盖全部 120 种组合，也不代表全部 110 细区均已外部验证。

资源页已移除依赖包外 ZIP、历史稿件及不存在线上地址的入口。
完整复现代码包、论文和补充材料继续单独保留，不作为网页运行依赖。
本次只将源码上传至新建私有仓库，未部署网页、未重训或重跑全队列；旧文件和环境保留。已完成的针对性接入检查见 docs/CODE_PROVENANCE.md。

Current PsychENCODE interface: see docs/PSYCHENCODE_INPUT.md. Two example paths cover old/new reference lookup; no full-cohort rerun, model fitting or performance estimation.
