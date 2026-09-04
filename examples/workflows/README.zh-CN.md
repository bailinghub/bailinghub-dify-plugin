# 确定性治理任务工作流

`bailinghub-governed-job.yml` 是一个可移植的 Dify Workflow 模板，不包含大模型节点，也不包含
凭据、部署地址、账号标识或生产路由。

## 导入与配置

1. 从 Dify Marketplace 安装 BailingHub `0.1.2`。
2. 为插件配置自部署 BailingHub 的 HTTPS 地址和独立 Client Token。
3. 在 Dify Studio 中导入 `bailinghub-governed-job.yml`。
4. 打开“提交治理任务”节点，把 `replace-with-a-client-allowed-route` 替换为该 Client Token
   已经放行的一条路由。
5. 先用无害测试指令运行，再接入真实业务数据。

工作流使用 `dify:<workflow_run_id>:submit` 生成 `request_id`，因此同一轮工作流中的工具节点
重试会继续使用同一个幂等标识；重新运行工作流则代表一项新请求。如果有界等待返回
`wait_timed_out: true`，应保存返回的 `job_id` 并在后续查询，不要重新提交一项替代任务。

模板输出 `job_id`、`request_id`、`status`、`terminal`、`wait_timed_out`、`result` 和 `error`。
`done` 表示成功；`error` 和 `rejected` 是终态失败；`queued`、`running`、`dispatched` 均为非终态。

这是一个通用适配器示例，不是任何已部署工作流的副本。实际路由、凭据、私有地址、请求标识和
端到端证据必须保存在部署组织自己的私有运维账本中。
