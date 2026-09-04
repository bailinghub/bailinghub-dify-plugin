# BailingHub 百灵中枢 Dify 工具插件

让 Dify Agent 或 Workflow 查询和操作已经接入自部署
[BailingHub 百灵中枢](https://github.com/bailinghub/bailinghub)的商城、SaaS、CRM、ERP
或其他业务后台。

具体能做什么，取决于业务系统主动声明的能力，以及管理员为当前 Dify 连接放行的路由。例如：

- 找出低库存商品并生成补货建议；
- 根据 Dify 表单或对话修改员工、客户资料；
- 发起订单退款，并在需要时由 BailingHub 暂停等待人工审批。

Dify 只负责提交请求和读取结果，不会拿到管理员、执行器或业务系统凭据。BailingHub 保留
路由限制、审批状态和审计轨迹，最终能否执行仍由业务系统判断。

插件只暴露三个控制面工具：

- `submit_governed_job`：向管理员已经配置的治理路由提交任务；
- `get_job`：查询任务当前状态和终态结果；
- `wait_for_job`：在限定时间内轮询任务，不无限占用工作流。

它不会把受治理的业务 API 直接导入 Dify。

```text
Dify Agent 或 Workflow
  -> BailingHub Dify 插件
     -> POST /run
     -> GET /jobs/{job_id}
        -> BailingHub 控制面
           -> 受治理执行器
              -> 业务系统
```

## 项目边界

这是一个独立维护的集成适配器，不是：

- ACC 规范的组成部分；
- BailingHub 服务端开源发行包中的内置模块；
- 与 ACC 或 BailingHub 共用版本号、Release 或发布节奏的子模块；
- Dify 官方合作、认证或背书。

依赖方向只有一个：本插件消费 BailingHub 对外公开的 Client API。详见
[项目边界](../docs/PROJECT_BOUNDARIES.md)和[兼容策略](../docs/COMPATIBILITY.md)。

## 获取插件

- 推荐：[从 Dify Marketplace 安装 BailingHub](https://marketplace.dify.ai/plugin/bailinghub/bailinghub)；
- 离线安装或固定版本：从[独立插件仓库 Releases](https://github.com/bailinghub/bailinghub-dify-plugin/releases)下载对应 `.difypkg`。

## 使用前提

- Dify 支持工具插件；
- Dify 可以访问一套自部署 BailingHub；
- 为该 Dify 应用创建一枚独立、仅允许必要路由的 Client Token；
- 除本机开发外，Dify 与 BailingHub 之间使用 HTTPS。

## 配置步骤

1. 在 BailingHub 中为当前 Dify 应用创建独立接入方。
2. 只放行 Dify 确实需要的路由，并设置合理限流。
3. 从 Dify Marketplace 安装本插件，或上传 Releases 中的固定版本安装包。
4. 配置：
   - `BailingHub 服务地址`：BailingHub 的 HTTPS 根地址；
   - `专用接入方令牌`：原始 Client Token，不要重复填写 `Bearer`。

不要使用管理员令牌、执行器令牌、工具供应商密钥或业务系统凭证代替 Client Token。

## 推荐工作流

1. 在工作流节点中确定性生成 `request_id`，例如
   `dify:<conversation-id>:<workflow-run-id>:<step-id>`。
2. 使用管理员提供的固定路由调用 `submit_governed_job`。
3. 保存返回的 `job_id`。
4. 使用 `wait_for_job` 做一次短时有界等待，或者在后续节点调用 `get_job`。
5. `done` 表示成功，`error` 和 `rejected` 表示终态失败。

`queued`、`running`、`dispatched` 都不是终态。等待超时后应继续查询同一个 `job_id`，
不要重新创建任务。重试同一业务请求时，应复用同一个 `request_id`，且不得改变请求含义和参数。

仓库提供了一个不依赖模型、可导入的示例：
[`examples/workflows/bailinghub-governed-job.yml`](../examples/workflows/bailinghub-governed-job.yml)。
它只提交一次任务，做一次有界等待，并输出同一个 `job_id` 和最新状态。运行前必须把路由占位符
替换为专用 Client Token 已放行的路由。详见[工作流示例说明](../examples/workflows/README.zh-CN.md)。

## 首次成功与反馈

请从[官网 Dify 接入路径](https://www.bailinghub.com/integrations#dify)开始。首次接入成功的客观标准是：
任务通过已配置路由提交后，在同一个 `job_id` 下到达终态；BailingHub 保留对应审批与审计状态；
Dify 全程没有获得管理员凭据或业务系统凭据。

无论 PASS、部分通过还是失败，都可以通过
[BailingHub 独立验证模板](https://github.com/bailinghub/bailinghub/issues/new?template=independent_validation.yml)
选择 Dify 路径反馈。不要提交 Token、模型 Key、个人信息或生产业务数据。

## 安全边界

- BailingHub 会再次使用接入方路由白名单约束路由。
- 插件不接收 `project` 和 `profile`，模型无法覆盖这些治理元数据。
- 响应限制为 1 MiB，并只输出任务状态和结果所需字段。
- 任意上游响应正文不会被原样暴露为错误。
- 非本机地址禁止使用明文 HTTP。
- 最终业务授权仍由业务系统负责。

本插件只负责把 Dify 接入治理执行链路，不是最终授权边界，也不会让模型输出天然可信。

## 开发与发布

本项目使用独立版本、独立测试和独立发布流程。开发命令及打包方式见英文
[README](../README.md)与[发布说明](../docs/RELEASING.md)。

## 许可证

Apache License 2.0，详见 [LICENSE](../LICENSE)。
