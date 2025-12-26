<div align="center">

# 群管助手 (Group Admin)

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/KroMiose/nekro-agent)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-OneBot%20v11-orange.svg)](https://onebot.dev/)

完整的群组管理工具集，赋予 AI 在群聊中进行各种管理操作的能力。

[功能特性](#主要功能) • [快速开始](#安装) • [配置说明](#配置说明) • [使用示例](#使用场景示例)

</div>

## 主要功能

- **成员管理**: 禁言、全体禁言、踢人、拉黑、改群昵称、改头衔、设管理员
- **消息管理**: 撤回消息、设置精华消息
- **群设置**: 改群名、改群头像、发群公告
- **分群配置**: 支持为不同群设置不同的管理规则
- **配置热更新**: 配置修改后立即生效，无需重启

## 权限模式

支持两种权限模式（通过配置项控制）:
1. `check_requester`: 检查请求者权限，只有有权限的用户才能让 AI 帮忙执行操作
2. `ai_autonomous`: AI 自主判断，只要 AI 有管理权限就可以执行

## 配置层级

支持全局配置和分群配置：
- **全局配置**: 作为默认配置，适用于所有没有单独配置的群
- **分群配置**: 为特定群单独设置，优先级高于全局配置

## 权限等级

超级管理员 > 群主 > 管理员 > 普通成员

## 分群配置管理

### 通过 AI 工具方法管理

你可以通过对话与 AI 交互来管理分群配置：

#### 1. 获取群组列表

```
你：获取所有群组列表
AI：[调用工具群管_获取群组列表]
```

#### 2. 查看群配置

```
你：查看群 123456789 的配置
AI：[调用工具群管_查看群配置]
```

#### 3. 设置群配置

```
你：为群 123456789 设置权限模式为 ai_autonomous
AI：[调用工具群管_设置群配置]
```

#### 4. 全局同步

```
你：将全局配置同步到所有群
AI：[调用工具群管_全局同步所有群]
```

#### 5. 复制配置到所有群

```
你：将群 123456789 的配置复制到所有其他群
AI：[调用工具群管_复制配置到所有群]
```

#### 6. 重置群配置

```
你：将群 123456789 的配置重置为全局默认
AI：[调用工具群管_重置群配置]
```

### 配置热更新

- 所有配置修改都会立即生效
- 配置会缓存 60 秒以提高性能
- 修改配置时会自动清除相关缓存
- 无需重启插件或服务

### 可用配置项

| 配置键 | 类型 | 说明 | 可选值 |
|---------|------|------|--------|
| PERMISSION_MODE | 字符串 | 权限模式 | check_requester, ai_autonomous |
| ENABLE_MUTE | 布尔 | 允许禁言 | true, false |
| ENABLE_MUTE_ALL | 布尔 | 允许全体禁言 | true, false |
| ENABLE_KICK | 布尔 | 允许踢人 | true, false |
| ENABLE_KICK_AND_BAN | 布尔 | 允许踢出并拉黑 | true, false |
| ENABLE_SET_CARD | 布尔 | 允许修改群昵称 | true, false |
| ENABLE_SET_TITLE | 布尔 | 允许设置头衔 | true, false |
| ENABLE_SET_ADMIN | 布尔 | 允许设置管理员 | true, false |
| ENABLE_DELETE_MSG | 布尔 | 允许撤回消息 | true, false |
| ENABLE_SET_ESSENCE | 布尔 | 允许设置精华 | true, false |
| ENABLE_SET_GROUP_NAME | 布尔 | 允许修改群名称 | true, false |
| ENABLE_SET_GROUP_PORTRAIT | 布尔 | 允许修改群头像 | true, false |
| ENABLE_SEND_NOTICE | 布尔 | 允许发布群公告 | true, false |
| ENABLE_ADMIN_REPORT | 布尔 | 启用管理操作报告 | true, false |
| MAX_MUTE_DURATION | 整数 | 最大禁言时长（秒） | >= 0 |

### 配置文件位置

分群配置存储在：`data/group_configs.json`

## 使用方法

此插件由 AI 根据用户请求或自主判断调用，用户可以通过对话请求 AI 执行管理操作。

## 安装

1. 将 `group_admin` 文件夹复制到 nekro-agent 的 `plugins` 目录
2. 重启 nekro-agent 或重新加载插件
3. 在插件配置页面进行配置

## 配置说明

### 全局配置项

- **权限模式**: 选择 AI 执行管理操作时的权限检查方式
- **超级管理员QQ列表**: 拥有最高权限的QQ号列表
- **受保护用户QQ列表**: 这些用户不能被任何管理操作影响（超级管理员除外）
- **最大禁言时长**: 单次禁言的最大时长
- **启用管理操作报告**: 启用后，管理操作将发送报告给管理频道

### AI 敏感功能开关

以下功能涉及敏感操作，建议谨慎开启：

- **允许禁言**: AI 可以禁言或解禁群成员
- **允许全体禁言**: AI 可以开启或关闭全体禁言
- **允许踢人**: AI 可以自主决定踢出群成员
- **允许踢出并拉黑**: AI 可以踢出并拉黑群成员
- **允许改群昵称**: AI 可以修改群成员的群昵称
- **允许设置头衔**: AI 可以设置群成员头衔
- **允许设置管理员**: AI 可以设置或取消群管理员
- **允许撤回消息**: AI 可以撤回群消息
- **允许设置精华**: AI 可以设置精华消息
- **允许改群名**: AI 可以修改群名称
- **允许改群头像**: AI 可以修改群头像
- **允许发群公告**: AI 可以发布群公告

## 使用场景示例

### 场景 1：不同群使用不同权限模式

```python
# 群A：AI自主模式
群管_设置群配置("PERMISSION_MODE", "ai_autonomous")

# 群B：检查请求者权限模式
群管_设置群配置("PERMISSION_MODE", "check_requester")
```

### 场景 2：不同群启用不同功能

```python
# 严格管理的群：启用踢人和拉黑
群管_设置群配置("ENABLE_KICK", "true")
群管_设置群_config("ENABLE_KICK_AND_BAN", "true")

# 宽松管理的群：仅启用禁言
群管_设置群_config("ENABLE_KICK", "false")
群管_设置群_config("ENABLE_MUTE", "true")
```

### 场景 3：不同群的禁言时长限制

```python
# 群A：最大禁言1小时
群管_设置群_config("MAX_MUTE_DURATION", "3600")

# 群B：最大禁言1天
群管_设置群_config("MAX_MUTE_DURATION", "86400")
```

### 场景 4：全局同步配置

```python
# 将全局配置应用到所有群
群管_全局同步所有群()
```

### 场景 5：复制配置到所有群

```python
# 将某个群的配置复制到所有其他群
群管_复制配置到所有群(123456789)
```

## 注意事项

1. **配置兼容性**：保持全局配置不变，确保向后兼容
2. **数据持久化**：使用 JSON 文件存储，确保配置持久化
3. **错误处理**：处理配置文件读写异常
4. **性能优化**：缓存配置数据，避免频繁文件读写
5. **安全性**：验证配置值的有效性，防止非法配置

## 故障排除

### 问题：配置未生效

**可能原因：**
- 配置缓存未清除
- 配置项名称错误

**解决方法：**
- 等待 60 秒让缓存过期
- 检查配置项名称是否正确
- 查看日志确认配置是否保存成功

### 问题：获取群组列表失败

**可能原因：**
- OneBot 服务未启动
- Bot 未登录
- 网络连接问题

**解决方法：**
- 检查 OneBot 服务状态
- 确认 Bot 已登录
- 检查网络连接

## 更新日志

### v1.0.0 (2025-12-26)

#### 新增功能
- ✨ 完整的群组管理工具集
- ✨ 成员管理功能：禁言、全体禁言、踢人、拉黑、改群昵称、改头衔、设管理员
- ✨ 消息管理功能：撤回消息、设置精华消息
- ✨ 群设置功能：改群名、改群头像、发群公告
- ✨ 分群配置：支持为不同群设置不同的管理规则
- ✨ 配置热更新：配置修改后立即生效，无需重启
- ✨ 两种权限模式：check_requester 和 ai_autonomous
- ✨ 权限等级系统：超级管理员 > 群主 > 管理员 > 普通成员
- ✨ 受保护用户列表
- ✨ 管理操作报告功能

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 作者

**小九**

## 致谢

感谢 [nekro-agent](https://github.com/KroMiose/nekro-agent) 项目提供的插件框架支持。

## 项目链接

- [nekro-agent](https://github.com/KroMiose/nekro-agent) - 主项目
- [Issue Tracker](https://github.com/KroMiose/nekro-agent/issues) - 问题反馈
- [Discussions](https://github.com/KroMiose/nekro-agent/discussions) - 讨论区

## 版本

v1.0.0

## 许可证

MIT License

## 作者

小九

## 项目链接

https://github.com/KroMiose/nekro-agent

## 版本

v1.0.0
