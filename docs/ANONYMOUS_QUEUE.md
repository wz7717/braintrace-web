# Anonymous single-machine queue / 免登录单机队列

This edition is prepared locally; it has not been pushed to GitHub or deployed.
No login is required. Every browser receives an independent, random HttpOnly session cookie.
The server holds its verifier and a separate CSRF token in memory. Upload, task, JSON and CSV access
are checked against that session. Knowing a task or upload ID is insufficient to access it from another session.
Saved examples and allowlisted documentation remain public; user uploads and job directories have no file-serving route.

## 默认限额

| 项目 | 默认值 |
|---|---|
| 单会话活动任务 | 1 个，包括排队和运行 |
| 单会话提交次数 | 滚动 30 分钟最多 4 次，成功受理即计入；失败也计入 |
| 单 IP | 最多 3 个活动任务，滚动 30 分钟最多 12 次提交 |
| 全站活动队列 | 最多 8 个，按受理顺序，始终只有 1 个推断进程任务运行 |
| 上传 | 每会话最多 2 个待运行文件；CEL 80 MiB，猕猴 8 MiB |
| 输入缓存 | 每会话 96 MiB，全站 160 MiB；包含接收中的预留和活动任务输入 |
| 上传频率 | 每会话每分钟 10 次；所有写请求每会话 30 次、每 IP 90 次 |
| 创建匿名会话 | 每 IP 每小时 10 次；全站最多 1000 个活动会话 |
| 等待上限 | 15 分钟，超时不启动推断，不自动重提 |
| 推断进程上限 | 猕猴 120 秒、人类 240 秒；原人类后端的内部 180 秒限制仍保留 |
| 数据保留 | 待运行文件、已完成结果各 30 分钟；会话空闲 30 分钟或总时长 2 小时过期 |
| HTTP 接收 | 最多 16 个连接处理线程；上传体总时限 60 秒 |

“每人”实际按浏览器会话并辅以 IP 限额实施，没有实名身份。相同浏览器的多个标签页共享限额。
无痕窗口或清除 Cookie 会形成新会话，IP 限额继续生效；不同 IP 仍可能绕过匿名限额。
共享校园/实验室网络的访客也共享 IP 限额。反向代理必须按部署说明覆盖客户端 IP 头。
未启用代理头时按实际连接地址计数，代理后的所有用户可能被归为 127.0.0.1。

上传与输入规范确认后才能入队。入队将文件缓存转交给任务，不能使用原 upload_id 再发新任务。
提交响应断线可使用相同 request_key 重试；同一会话、同一请求只生成一个任务。
重新提交不同任务需重新上传。任务失败和限额错误均明确返回，不会伪造成功或悄悄更换配置。

## 超时和故障恢复

每项推断使用独立 Python 子进程和随机工作目录，冻结科学后端原样调用。
Windows 使用 Job Object 把该进程及其 Python/R 子进程绑定到同一生命周期。
超过期限、会话失效或服务正常关闭时回收整个任务进程树，清理该任务临时目录并释放输入预算。
失败任务保留错误状态，下一项继续；清理失败则暂停新计算，避免把未回收的任务当作已恢复。
Linux 分支使用独立进程组，但本轮未验证 Linux 或跨操作系统科学运行。

这是单服务进程的内存队列。重启会丢失会话、排队项和未下载结果，不自动重放任务。
Windows 服务进程意外退出会由 Job Object 回收计算子进程；磁盘上的异常退出残留需要管理员在确认服务停止后清理专用工作根目录。
超时和正常关闭路径已覆盖自动清理；没有声称具备断电后持久化恢复。
工作根目录应专用于此服务、仅服务账户可访问，不应与另一个实例共用。
不要用多个 HTTP worker/实例扩展此版本，否则会话、限额和队列不共享。

## 配置和针对性检查

默认值在 queue.example.json。需要调整时在组装后的运行目录另存 queue.local.json，
用 --queue-config 指定。值必须为正整数，未知字段拒绝；不改变模型、基因面板或评分规则。
人类实时推断需要 ASCII 工作路径，例如 C:/BrainTraceWork/anonymous_queue。
不要把 queue.local.json、runtime.local.json、上传、结果或工作目录提交至仓库。

只检查本次服务层变更：

```text
python -X utf8 -B tests/check_anonymous_queue.py
```

该脚本使用模拟输入和真实可终止测试进程，不执行模型。它覆盖两个独立浏览器会话、
跨会话上传/任务/CSV 拒绝、Cookie/CSRF、请求幂等、FIFO、会话/IP/全站限额、
输入预留及中断释放、结果/会话过期、排队超时、进程树超时/崩溃/关闭及下一任务恢复。
真实推断接入检查单独调用 tests/check_anonymous_live.py；需要完整运行资产和原冻结环境。
它只运行一个成年 HIP 样本及一个人类 CEL（RAW/RANK），对照既有保存结果，不做队列重估。

会话隔离是应用层访问控制，不是针对任意代码的操作系统沙箱；不接收用户脚本或任意执行命令。
本版按小规模研究演示配置，未作公网压测或抗分布式滥用承诺。
