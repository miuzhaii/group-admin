"""
# 群管助手 (Group Admin)

完整的群组管理工具集，赋予 AI 在群聊中进行各种管理操作的能力。

## 主要功能

- **成员管理**: 禁言、全体禁言、踢人、拉黑、改群昵称、改头衔、设管理员
- **消息管理**: 撤回消息、设置精华消息
- **群设置**: 改群名、改群头像、发群公告
- **分群配置**: 支持为不同群设置不同的管理规则

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

## 使用方法

此插件由 AI 根据用户请求或自主判断调用，用户可以通过对话请求 AI 执行管理操作。
"""

from enum import IntEnum
from typing import Any, Literal, Optional, List

from pydantic import Field

from nekro_agent.adapters.onebot_v11.core.bot import get_bot
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType, ExtraField
from nekro_agent.api import core, message
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.config import config
from nekro_agent.schemas.chat_message import ChatType

from .config_manager import GroupConfigManager


# ============== 插件实例 ==============

plugin = NekroPlugin(
    name="群管助手",
    module_name="group_admin",
    description="完整的群组管理工具集，提供禁言、踢人、改群昵称、设管理员等管理功能",
    version="1.0.1",
    author="XiaoJiu",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11"],
)


# ============== 配置类 ==============

@plugin.mount_config()
class GroupAdminConfig(ConfigBase):
    """群管助手配置"""

    ALLOW_GROUPS: List[str] = Field(
        default=[],
        title="允许使用群管功能的群组列表",
        description="如果为空，则允许所有群组使用群管功能。配置了分群配置的群会自动添加到此列表。",
        json_schema_extra=ExtraField(sub_item_name="群组").model_dump(),
    )

    PERMISSION_MODE: Literal["check_requester", "ai_autonomous"] = Field(
        default="ai_autonomous",
        title="权限模式",
        description="check_requester: 检查请求者权限; ai_autonomous: AI自主判断执行",
    )
    
    SUPER_ADMINS: list[str] = Field(
        default=[],
        title="超级管理员QQ列表",
        description="拥有最高权限的QQ号列表，不受任何限制",
    )
    
    PROTECTED_USERS: list[str] = Field(
        default=[],
        title="受保护用户QQ列表",
        description="这些用户不能被任何管理操作影响（超级管理员除外）",
    )
    
    MAX_MUTE_DURATION: int = Field(
        default=60 * 60 * 24 * 30,
        title="最大禁言时长（秒）",
        description="单次禁言的最大时长，默认30天",
    )
    
    ENABLE_ADMIN_REPORT: bool = Field(
        default=True,
        title="启用管理操作报告",
        description="启用后，管理操作将发送报告给管理频道",
    )
    
    # ===== AI敏感功能开关 =====
    
    ENABLE_MUTE: bool = Field(
        default=True,
        title="【AI敏感功能】允许禁言",
        description="开启后AI可以禁言或解禁群成员",
    )
    
    ENABLE_MUTE_ALL: bool = Field(
        default=False,
        title="【AI敏感功能】允许全体禁言",
        description="开启后AI可以开启或关闭全体禁言，建议谨慎开启",
    )
    
    ENABLE_KICK: bool = Field(
        default=False,
        title="【AI敏感功能】允许踢人",
        description="开启后AI可以自主决定踢出群成员，建议谨慎开启",
    )
    
    ENABLE_KICK_AND_BAN: bool = Field(
        default=False,
        title="【AI敏感功能】允许踢出并拉黑",
        description="开启后AI可以踢出并拉黑群成员，建议谨慎开启",
    )
    
    ENABLE_SET_CARD: bool = Field(
        default=True,
        title="【AI敏感功能】允许改群昵称",
        description="开启后AI可以修改群成员的群昵称",
    )
    
    ENABLE_SET_TITLE: bool = Field(
        default=False,
        title="【AI敏感功能】允许设置头衔",
        description="开启后AI可以设置群成员头衔，建议谨慎开启",
    )
    
    ENABLE_SET_ADMIN: bool = Field(
        default=False,
        title="【AI敏感功能】允许设置管理员",
        description="开启后AI可以设置或取消群管理员，建议谨慎开启",
    )
    
    ENABLE_DELETE_MSG: bool = Field(
        default=False,
        title="【AI敏感功能】允许撤回消息",
        description="开启后AI可以撤回群消息，建议谨慎开启",
    )
    
    ENABLE_SET_ESSENCE: bool = Field(
        default=True,
        title="【AI敏感功能】允许设置精华",
        description="开启后AI可以设置精华消息",
    )
    
    ENABLE_SET_GROUP_NAME: bool = Field(
        default=False,
        title="【AI敏感功能】允许改群名",
        description="开启后AI可以修改群名称，建议谨慎开启",
    )
    
    ENABLE_SET_GROUP_PORTRAIT: bool = Field(
        default=False,
        title="【AI敏感功能】允许改群头像",
        description="开启后AI可以修改群头像，建议谨慎开启",
    )
    
    ENABLE_SEND_NOTICE: bool = Field(
        default=False,
        title="【AI敏感功能】允许发群公告",
        description="开启后AI可以发布群公告，建议谨慎开启",
    )


# 获取配置（每次调用时重新获取最新配置）
def get_admin_config() -> GroupAdminConfig:
    """获取最新的插件配置
    
    Returns:
        最新的配置对象
    """
    return plugin.get_config(GroupAdminConfig)

# 初始化分群配置管理器
group_config_manager = GroupConfigManager("data/group_configs.json")


# ============== 配置获取函数 ==============

async def get_effective_config(group_id: int) -> dict[str, Any]:
    """获取群的有效配置（分群配置优先）
    
    Args:
        group_id: 群号
        
    Returns:
        合并后的配置字典
    """
    # 每次都重新获取最新的全局配置
    admin_config = get_admin_config()
    
    # 将全局配置转换为字典
    global_config_dict = {
        "PERMISSION_MODE": admin_config.PERMISSION_MODE,
        "SUPER_ADMINS": admin_config.SUPER_ADMINS,
        "PROTECTED_USERS": admin_config.PROTECTED_USERS,
        "MAX_MUTE_DURATION": admin_config.MAX_MUTE_DURATION,
        "ENABLE_ADMIN_REPORT": admin_config.ENABLE_ADMIN_REPORT,
        "ENABLE_MUTE": admin_config.ENABLE_MUTE,
        "ENABLE_MUTE_ALL": admin_config.ENABLE_MUTE_ALL,
        "ENABLE_KICK": admin_config.ENABLE_KICK,
        "ENABLE_KICK_AND_BAN": admin_config.ENABLE_KICK_AND_BAN,
        "ENABLE_SET_CARD": admin_config.ENABLE_SET_CARD,
        "ENABLE_SET_TITLE": admin_config.ENABLE_SET_TITLE,
        "ENABLE_SET_ADMIN": admin_config.ENABLE_SET_ADMIN,
        "ENABLE_DELETE_MSG": admin_config.ENABLE_DELETE_MSG,
        "ENABLE_SET_ESSENCE": admin_config.ENABLE_SET_ESSENCE,
        "ENABLE_SET_GROUP_NAME": admin_config.ENABLE_SET_GROUP_NAME,
        "ENABLE_SET_GROUP_PORTRAIT": admin_config.ENABLE_SET_GROUP_PORTRAIT,
        "ENABLE_SEND_NOTICE": admin_config.ENABLE_SEND_NOTICE,
    }
    
    # 获取合并后的配置
    return await group_config_manager.get_group_config(group_id, global_config_dict)


# ============== 权限等级枚举 ==============

class PermissionLevel(IntEnum):
    """权限等级"""
    MEMBER = 1       # 普通成员
    ADMIN = 2        # 管理员
    OWNER = 3        # 群主
    SUPER_ADMIN = 4  # 超级管理员


# ============== 权限检查工具函数 ==============

async def get_bot_permission_level(group_id: int) -> PermissionLevel:
    """获取bot在群内的权限等级
    
    Args:
        group_id: 群号
        
    Returns:
        PermissionLevel: bot的权限等级
    """
    admin_config = get_admin_config()
    try:
        # 获取bot的QQ号
        bot_info = await get_bot().get_login_info()
        bot_qq = str(bot_info.get("user_id", ""))
        
        # 检查是否是超级管理员
        if bot_qq in admin_config.SUPER_ADMINS:
            return PermissionLevel.SUPER_ADMIN
        
        # 获取bot在群内的成员信息
        member_info = await get_bot().get_group_member_info(
            group_id=group_id,
            user_id=int(bot_qq),
            no_cache=True
        )
        role = member_info.get("role", "member")
        
        if role == "owner":
            return PermissionLevel.OWNER
        elif role == "admin":
            return PermissionLevel.ADMIN
        else:
            return PermissionLevel.MEMBER
    except Exception as e:
        core.logger.error(f"获取bot权限失败: {e}")
        return PermissionLevel.MEMBER


async def get_user_permission_level(group_id: int, user_qq: str) -> PermissionLevel:
    """获取用户在群内的权限等级
    
    Args:
        group_id: 群号
        user_qq: 用户QQ号
        
    Returns:
        PermissionLevel: 权限等级
    """
    admin_config = get_admin_config()
    # 检查是否是超级管理员
    if user_qq in admin_config.SUPER_ADMINS:
        return PermissionLevel.SUPER_ADMIN
    
    try:
        # 获取群成员信息
        member_info = await get_bot().get_group_member_info(
            group_id=group_id,
            user_id=int(user_qq),
            no_cache=True
        )
        role = member_info.get("role", "member")
        
        if role == "owner":
            return PermissionLevel.OWNER
        elif role == "admin":
            return PermissionLevel.ADMIN
        else:
            return PermissionLevel.MEMBER
    except Exception as e:
        core.logger.error(f"获取用户权限失败: {e}")
        return PermissionLevel.MEMBER


async def check_permission(
    ctx: AgentCtx,
    group_id: int,
    target_qq: str,
    required_level: PermissionLevel = PermissionLevel.ADMIN,
    operation_name: str = "此操作",
    requester_qq: Optional[str] = None
) -> tuple[bool, str]:
    """检查权限（使用分群配置）
    
    Args:
        ctx: 上下文
        group_id: 群号
        target_qq: 目标用户QQ
        required_level: 执行操作需要的最低权限等级
        operation_name: 操作名称（用于错误提示）
        requester_qq: 请求者QQ号（check_requester模式下必须提供）
        
    Returns:
        tuple[bool, str]: (是否有权限, 提示信息)
    """
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 先检查bot自身的权限
    bot_level = await get_bot_permission_level(group_id)
    
    if bot_level < required_level:
        level_names = {
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.OWNER: "群主",
            PermissionLevel.SUPER_ADMIN: "超级管理员",
        }
        return False, f"bot权限不足：{operation_name}需要{level_names[required_level]}及以上权限，bot当前权限为 {level_names[bot_level]}"
    
    # 获取目标用户的权限等级（两种模式都需要）
    try:
        target_member_info = await get_bot().get_group_member_info(
            group_id=group_id,
            user_id=int(target_qq),
            no_cache=True
        )
        target_role = target_member_info.get("role", "member")
        
        # 映射角色到权限等级
        role_to_level = {
            "owner": PermissionLevel.OWNER,
            "admin": PermissionLevel.ADMIN,
            "member": PermissionLevel.MEMBER
        }
        target_level = role_to_level.get(target_role, PermissionLevel.MEMBER)
        
        # 检查QQ协议的特殊限制
        if target_role == "owner":
            return False, f"无法对群主执行{operation_name}（QQ协议限制：不能禁言/踢出群主）"
    except Exception as e:
        core.logger.error(f"获取目标用户权限失败: {e}")
        # 如果获取失败，继续后续检查
        target_level = PermissionLevel.MEMBER
    
    # AI自主模式下不检查请求者权限
    if effective_config.get("PERMISSION_MODE") == "ai_autonomous":
        # 检查目标是否受保护
        protected_users = effective_config.get("PROTECTED_USERS", [])
        if target_qq in protected_users:
            return False, f"用户 {target_qq} 是受保护用户，无法执行{operation_name}"
        return True, "AI自主模式"
    
    # check_requester 模式下必须提供请求者QQ
    if not requester_qq:
        return False, f"权限检查模式下需要提供请求者QQ（requester_qq参数），请让AI在调用时传入发起请求的用户QQ号"
    
    # 获取请求者权限
    requester_level = await get_user_permission_level(group_id, requester_qq)
    
    # 检查请求者是否有足够权限
    if requester_level < required_level:
        level_names = {
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.OWNER: "群主",
            PermissionLevel.SUPER_ADMIN: "超级管理员",
        }
        return False, f"权限不足：{operation_name}需要{level_names[required_level]}及以上权限，用户 {requester_qq} 当前权限为 {level_names[requester_level]}"
    
    # 检查目标是否受保护
    protected_users = effective_config.get("PROTECTED_USERS", [])
    if target_qq in protected_users and requester_level < PermissionLevel.SUPER_ADMIN:
        return False, f"用户 {target_qq} 是受保护用户，只有超级管理员才能操作"
    
    # 获取目标权限
    target_level = await get_user_permission_level(group_id, target_qq)
    
    # 检查是否有权操作目标用户（只能操作权限比自己低的用户）
    if target_level >= requester_level and requester_level < PermissionLevel.SUPER_ADMIN:
        level_names = {
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.OWNER: "群主",
            PermissionLevel.SUPER_ADMIN: "超级管理员",
        }
        return False, f"无法对同级或更高权限的用户执行{operation_name}（目标用户权限: {level_names[target_level]}）"
    
    return True, "权限检查通过"


async def check_requester_permission(
    group_id: int,
    requester_qq: Optional[str],
    required_level: PermissionLevel,
    operation_name: str
) -> tuple[bool, str]:
    """仅检查请求者权限（不涉及目标用户的操作）
    
    Args:
        group_id: 群号
        requester_qq: 请求者QQ号
        required_level: 执行操作需要的最低权限等级
        operation_name: 操作名称
        
    Returns:
        tuple[bool, str]: (是否有权限, 提示信息)
    """
    # 先检查bot自身的权限
    bot_level = await get_bot_permission_level(group_id)
    
    if bot_level < required_level:
        level_names = {
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.OWNER: "群主",
            PermissionLevel.SUPER_ADMIN: "超级管理员",
        }
        return False, f"bot权限不足：{operation_name}需要{level_names[required_level]}及以上权限，bot当前权限为 {level_names[bot_level]}"
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # AI自主模式下不检查请求者权限
    if effective_config.get("PERMISSION_MODE") == "ai_autonomous":
        return True, "AI自主模式"
    
    # check_requester 模式下必须提供请求者QQ
    if not requester_qq:
        return False, f"权限检查模式下需要提供请求者QQ（requester_qq参数），请让AI在调用时传入发起请求的用户QQ号"
    
    # 获取请求者权限
    requester_level = await get_user_permission_level(group_id, requester_qq)
    
    # 检查请求者是否有足够权限
    if requester_level < required_level:
        level_names = {
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.OWNER: "群主",
            PermissionLevel.SUPER_ADMIN: "超级管理员",
        }
        return False, f"权限不足：{operation_name}需要{level_names[required_level]}及以上权限，用户 {requester_qq} 当前权限为 {level_names[requester_level]}"
    
    return True, "权限检查通过"


def parse_chat_key(ctx: AgentCtx) -> tuple[str, str]:
    """解析聊天标识
    
    Returns:
        tuple[str, str]: (chat_type, chat_id)
    """
    if ctx.channel_id:
        return ctx.channel_id.split("_")
    return ctx.chat_key.split("_")


async def send_admin_report(ctx: AgentCtx, operation: str, details: str):
    """发送管理操作报告给管理频道"""
    admin_config = get_admin_config()
    if admin_config.ENABLE_ADMIN_REPORT and config.ADMIN_CHAT_KEY:
        await message.send_text(
            config.ADMIN_CHAT_KEY,
            f"[群管操作报告]\n操作: {operation}\n{details}\n来源会话: {ctx.chat_key}",
            ctx,
        )


# ============== 提示词注入 ==============

@plugin.mount_prompt_inject_method(name="group_admin_prompt_inject")
async def group_admin_prompt_inject(_ctx: AgentCtx):
    """向AI提示词注入群管助手相关内容"""
    # 获取当前群的配置
    chat_type, chat_id = parse_chat_key(_ctx)
    
    # 获取最新的全局配置
    admin_config = get_admin_config()
    
    if chat_type == ChatType.GROUP.value:
        group_id = int(chat_id)
        effective_config = await get_effective_config(group_id)
        
        # 检查是否有分群配置
        all_configs = await group_config_manager.list_group_configs()
        group_key = str(group_id)
        has_custom_config = group_key in all_configs
        
        if has_custom_config:
            config_mode = "分群配置（优先级高于全局配置）"
        else:
            config_mode = "全局默认配置"
    else:
        # 非群聊，使用全局配置
        effective_config = {
            "PERMISSION_MODE": admin_config.PERMISSION_MODE,
            "ENABLE_MUTE": admin_config.ENABLE_MUTE,
            "ENABLE_MUTE_ALL": admin_config.ENABLE_MUTE_ALL,
            "ENABLE_KICK": admin_config.ENABLE_KICK,
            "ENABLE_KICK_AND_BAN": admin_config.ENABLE_KICK_AND_BAN,
            "ENABLE_SET_CARD": admin_config.ENABLE_SET_CARD,
            "ENABLE_SET_TITLE": admin_config.ENABLE_SET_TITLE,
            "ENABLE_SET_ADMIN": admin_config.ENABLE_SET_ADMIN,
            "ENABLE_DELETE_MSG": admin_config.ENABLE_DELETE_MSG,
            "ENABLE_SET_ESSENCE": admin_config.ENABLE_SET_ESSENCE,
            "ENABLE_SET_GROUP_NAME": admin_config.ENABLE_SET_GROUP_NAME,
            "ENABLE_SET_GROUP_PORTRAIT": admin_config.ENABLE_SET_GROUP_PORTRAIT,
            "ENABLE_SEND_NOTICE": admin_config.ENABLE_SEND_NOTICE,
        }
        config_mode = "全局默认配置"
    
    if effective_config.get("PERMISSION_MODE") == "check_requester":
        mode_desc = """当前模式：检查请求者权限模式
- 执行管理操作时，你需要传入 requester_qq 参数（发起请求的用户QQ号）
- 系统会通过 OneBot API 验证该用户是否有足够权限执行操作
- 你可以从消息历史中找到发起请求的用户QQ号"""
    else:
        mode_desc = """当前模式：AI自主判断模式
- 你可以根据情况自主决定是否执行管理操作
- 不需要传入 requester_qq 参数"""
    
    # 根据配置动态生成可用功能列表
    available_features = []
    
    # 成员管理
    if effective_config.get("ENABLE_MUTE"):
        available_features.append("- 禁言/解禁群成员")
    if effective_config.get("ENABLE_MUTE_ALL"):
        available_features.append("- 全体禁言")
    if effective_config.get("ENABLE_KICK"):
        available_features.append("- 踢出成员")
    if effective_config.get("ENABLE_KICK_AND_BAN"):
        available_features.append("- 踢出并拉黑")
    if effective_config.get("ENABLE_SET_CARD"):
        available_features.append("- 修改群昵称")
    if effective_config.get("ENABLE_SET_TITLE"):
        available_features.append("- 设置专属头衔")
    if effective_config.get("ENABLE_SET_ADMIN"):
        available_features.append("- 设置/取消管理员")
    
    # 消息管理
    if effective_config.get("ENABLE_DELETE_MSG"):
        available_features.append("- 撤回消息")
    if effective_config.get("ENABLE_SET_ESSENCE"):
        available_features.append("- 设置精华消息")
    
    # 群设置
    if effective_config.get("ENABLE_SET_GROUP_NAME"):
        available_features.append("- 修改群名称")
    if effective_config.get("ENABLE_SET_GROUP_PORTRAIT"):
        available_features.append("- 修改群头像")
    if effective_config.get("ENABLE_SEND_NOTICE"):
        available_features.append("- 发布群公告")
    
    features_text = "\n".join(available_features) if available_features else "（暂无可用功能）"
    
    # 检查 ALLOW_GROUPS 配置
    if len(admin_config.ALLOW_GROUPS) == 0:
        allow_groups_status = "所有群组均可使用群管功能"
    else:
        chat_type, chat_id = parse_chat_key(_ctx)
        if chat_type == ChatType.GROUP.value:
            group_id = str(chat_id)
            if group_id in admin_config.ALLOW_GROUPS:
                allow_groups_status = f"当前群 ({group_id}) 在允许列表中，可以使用群管功能"
            else:
                allow_groups_status = f"当前群 ({group_id}) 不在允许列表中，无法使用群管功能"
        else:
            allow_groups_status = "当前非群聊，群管功能可能受限"
    
    return f"""作为群管助手，你拥有以下群管理能力：
{features_text}

配置模式: {config_mode}

{mode_desc}

## 📋 群组访问控制
{allow_groups_status}

## ⚠️ 重要使用说明

### 功能开关状态
以下功能当前已**关闭**，请勿尝试调用：
{chr(10).join([f"- {name}" for name, enabled in [
    ("禁言/解禁", not effective_config.get("ENABLE_MUTE", False)),
    ("全体禁言", not effective_config.get("ENABLE_MUTE_ALL", False)),
    ("踢出成员", not effective_config.get("ENABLE_KICK", False)),
    ("踢出并拉黑", not effective_config.get("ENABLE_KICK_AND_BAN", False)),
    ("修改群昵称", not effective_config.get("ENABLE_SET_CARD", False)),
    ("设置专属头衔", not effective_config.get("ENABLE_SET_TITLE", False)),
    ("设置/取消管理员", not effective_config.get("ENABLE_SET_ADMIN", False)),
    ("撤回消息", not effective_config.get("ENABLE_DELETE_MSG", False)),
    ("设置精华消息", not effective_config.get("ENABLE_SET_ESSENCE", False)),
    ("修改群名称", not effective_config.get("ENABLE_SET_GROUP_NAME", False)),
    ("修改群头像", not effective_config.get("ENABLE_SET_GROUP_PORTRAIT", False)),
    ("发布群公告", not effective_config.get("ENABLE_SEND_NOTICE", False)),
] if enabled])}

### 分群配置查看
你可以使用以下工具查看分群配置：
- `群管_查看群配置`: 查看当前群或指定群的配置，包括功能开关状态

### 通过昵称查找成员（必须遵守）
当用户要求对某个昵称的成员执行管理操作时，**必须**按以下步骤进行：
1. 先调用 `群管_获取成员列表` 工具，传入昵称作为搜索关键词
2. 从返回的列表中找到匹配的成员及其QQ号
3. 使用找到的QQ号调用相应的管理操作工具（如 `群管_禁言用户`）

**错误示例**：
- 用户说："禁言下 救命啊家人们十分钟"
- ❌ 错误做法：直接使用发送消息的用户QQ号或随便猜测一个QQ号
- ✅ 正确做法：先调用 `群管_获取成员列表(search_keyword="救命啊家人们")`，找到匹配的QQ号，再禁言

### 群主限制
- QQ协议限制：**无法禁言或踢出群主**
- 如果尝试对群主执行禁言/踢出操作，系统会返回错误提示
- 在执行操作前，请先确认目标用户的角色

### 使用管理功能时请注意：
1. 谨慎使用管理权限，避免滥用
2. 执行操作前应确认理由充分
3. 所有操作都会被记录并可能报告给管理员
4. 权限等级：超级管理员 > 群主 > 管理员 > 普通成员
5. 只能对权限比操作者低的用户执行操作
6. 在权限检查模式下，需要提供 requester_qq 参数来验证权限
""".strip()


# ============== 成员管理功能 ==============

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_获取成员列表",
    description="获取群成员列表，支持按昵称或QQ号搜索成员。返回成员的QQ号、昵称、角色等信息。",
)
async def admin_get_member_list(_ctx: AgentCtx, search_keyword: str = "", requester_qq: Optional[str] = None) -> str:
    """获取群成员列表，支持搜索
    
    Args:
        search_keyword (str): 搜索关键词（QQ号或昵称），留空则返回所有成员
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 成员列表信息
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"获取成员列表仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 权限检查 - 获取成员列表需要管理员权限
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.ADMIN, "获取成员列表"
    )
    if not can_operate:
        return msg
    
    try:
        # 获取群成员列表
        member_list = await get_bot().get_group_member_list(group_id=group_id)
        
        # 搜索匹配的成员
        matched_members = []
        for member in member_list:
            user_id = str(member.get("user_id", ""))
            card = member.get("card", "") or member.get("nickname", "")
            role = member.get("role", "member")
            
            # 角色映射
            role_names = {
                "owner": "群主",
                "admin": "管理员",
                "member": "普通成员"
            }
            role_name = role_names.get(role, role)
            
            # 如果有搜索关键词，进行匹配
            if search_keyword:
                if search_keyword in user_id or search_keyword in card:
                    matched_members.append({
                        "qq": user_id,
                        "昵称": card,
                        "角色": role_name
                    })
            else:
                matched_members.append({
                    "qq": user_id,
                    "昵称": card,
                    "角色": role_name
                })
        
        if not matched_members:
            return f"未找到匹配 '{search_keyword}' 的成员"
        
        # 格式化输出
        if search_keyword:
            result = f"找到 {len(matched_members)} 个匹配 '{search_keyword}' 的成员：\n"
        else:
            result = f"群成员列表（共 {len(matched_members)} 人）：\n"
        
        for idx, member in enumerate(matched_members[:20], 1):  # 最多显示20个
            result += f"{idx}. QQ: {member['qq']}, 昵称: {member['昵称']}, 角色: {member['角色']}\n"
        
        if len(matched_members) > 20:
            result += f"...还有 {len(matched_members) - 20} 个成员未显示"
        
        core.logger.info(f"[群{chat_id}] 获取成员列表成功，搜索关键词: '{search_keyword}'，匹配数: {len(matched_members)}")
        return result
        
    except Exception as e:
        core.logger.error(f"获取成员列表失败: {e}")
        return f"获取成员列表失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_禁言用户",
    description="禁言群成员指定时长，设置时长为0则解除禁言。注意：无法禁言群主。权限检查模式下需提供requester_qq参数。",
)
async def admin_mute_user(_ctx: AgentCtx, user_qq: str, duration: int, report: str, requester_qq: Optional[str] = None) -> str:
    """禁言群成员（需要管理员及以上权限）
    
    Args:
        user_qq (str): 被禁言用户的QQ号
        duration (int): 禁言时长（秒），设置为0则解除禁言，最大30天
        report (str): 禁言理由，需详细说明原因
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供，用于验证权限
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        result = f"禁言功能仅支持群聊，当前频道类型: {chat_type}"
        core.logger.warning(f"[群管_禁言用户] {result}")
        return result
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_MUTE"):
        return "禁言功能未开启，无法执行此操作"
    
    core.logger.info(f"[群管_禁言用户] 收到请求: user_qq={user_qq}, duration={duration}, requester_qq={requester_qq}")
    
    # 权限检查（已在check_permission中检查目标用户角色）
    can_operate, msg = await check_permission(
        _ctx, group_id, user_qq,
        PermissionLevel.ADMIN, "禁言用户", requester_qq
    )
    core.logger.info(f"[群管_禁言用户] 权限检查结果: can_operate={can_operate}, msg={msg}")
    if not can_operate:
        return msg
    
    # 检查禁言时长
    if duration < 0:
        return "禁言时长不能为负数"
    admin_config = get_admin_config()
    max_duration = effective_config.get("MAX_MUTE_DURATION", admin_config.MAX_MUTE_DURATION)
    if duration > max_duration:
        return f"禁言时长不能超过 {max_duration // 86400} 天"
    
    try:
        core.logger.info(f"[群管_禁言用户] 调用 OneBot API: set_group_ban(group_id={group_id}, user_id={user_qq}, duration={duration})")
        await get_bot().set_group_ban(
            group_id=group_id,
            user_id=int(user_qq),
            duration=duration
        )
        
        action = "解除禁言" if duration == 0 else f"禁言 {duration} 秒"
        result = f"已对用户 {user_qq} 执行{action}"
        
        await send_admin_report(_ctx, "禁言用户", f"目标: {user_qq}\n时长: {duration}秒\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"禁言用户失败: {e}", exc_info=True)
        return f"禁言用户失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_全体禁言",
    description="开启或关闭群全体禁言。权限检查模式下需提供requester_qq参数。",
)
async def admin_mute_all(_ctx: AgentCtx, enable: bool, report: str, requester_qq: Optional[str] = None) -> str:
    """全体禁言（需要管理员及以上权限）
    
    Args:
        enable (bool): True开启全体禁言，False关闭全体禁言
        report (str): 操作理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"全体禁言功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_MUTE_ALL"):
        return "全体禁言功能未开启，无法执行此操作"
    
    # 全体禁言只检查操作者权限，不针对特定用户
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.ADMIN, "全体禁言"
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_whole_ban(group_id=group_id, enable=enable)
        
        action = "开启" if enable else "关闭"
        result = f"已{action}全体禁言"
        
        await send_admin_report(_ctx, "全体禁言", f"操作: {action}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"全体禁言操作失败: {e}")
        return f"全体禁言操作失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_踢出成员",
    description="将成员踢出群聊。权限检查模式下需提供requester_qq参数。",
)
async def admin_kick_user(_ctx: AgentCtx, user_qq: str, report: str, requester_qq: Optional[str] = None) -> str:
    """踢出群成员（需要管理员及以上权限）
    
    Args:
        user_qq (str): 被踢出用户的QQ号
        report (str): 踢出理由，需详细说明原因
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"踢人功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_KICK"):
        return "踢人功能未开启，无法执行此操作"
    
    # 权限检查
    can_operate, msg = await check_permission(
        _ctx, group_id, user_qq,
        PermissionLevel.ADMIN, "踢出成员", requester_qq
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_kick(
            group_id=group_id,
            user_id=int(user_qq),
            reject_add_request=False
        )
        
        result = f"已将用户 {user_qq} 踢出群聊"
        
        await send_admin_report(_ctx, "踢出成员", f"目标: {user_qq}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"踢出成员失败: {e}")
        return f"踢出成员失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_踢出并拉黑",
    description="将成员踢出群聊并拉黑（禁止再次加群）。权限检查模式下需提供requester_qq参数。",
)
async def admin_kick_and_ban(_ctx: AgentCtx, user_qq: str, report: str, requester_qq: Optional[str] = None) -> str:
    """踢出并拉黑群成员（需要管理员及以上权限）
    
    Args:
        user_qq (str): 被踢出用户的QQ号
        report (str): 踢出并拉黑的理由，需详细说明原因
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"踢人功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_KICK_AND_BAN"):
        return "踢出并拉黑功能未开启，无法执行此操作"
    
    # 权限检查
    can_operate, msg = await check_permission(
        _ctx, group_id, user_qq,
        PermissionLevel.ADMIN, "踢出并拉黑", requester_qq
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_kick(
            group_id=group_id,
            user_id=int(user_qq),
            reject_add_request=True
        )
        
        result = f"已将用户 {user_qq} 踢出群聊并拉黑"
        
        await send_admin_report(_ctx, "踢出并拉黑", f"目标: {user_qq}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"踢出并拉黑失败: {e}")
        return f"踢出并拉黑失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_修改群昵称",
    description="修改群成员的群昵称（群名片）。权限检查模式下需提供requester_qq参数。",
)
async def admin_set_group_card(_ctx: AgentCtx, user_qq: str, card: str, report: str, requester_qq: Optional[str] = None) -> str:
    """修改群成员昵称（需要管理员及以上权限）
    
    Args:
        user_qq (str): 目标用户的QQ号
        card (str): 新的群昵称，留空则删除群昵称
        report (str): 修改理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"修改群昵称功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SET_CARD"):
        return "修改群昵称功能未开启，无法执行此操作"
    
    # 权限检查
    can_operate, msg = await check_permission(
        _ctx, group_id, user_qq,
        PermissionLevel.ADMIN, "修改群昵称", requester_qq
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_card(
            group_id=group_id,
            user_id=int(user_qq),
            card=card
        )
        
        action = f"修改为 '{card}'" if card else "清空"
        result = f"已将用户 {user_qq} 的群昵称{action}"
        
        await send_admin_report(_ctx, "修改群昵称", f"目标: {user_qq}\n新昵称: {card or '(空)'}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"修改群昵称失败: {e}")
        return f"修改群昵称失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_设置专属头衔",
    description="设置群成员的专属头衔（仅群主可操作）。权限检查模式下需提供requester_qq参数。",
)
async def admin_set_special_title(_ctx: AgentCtx, user_qq: str, title: str, report: str, requester_qq: Optional[str] = None) -> str:
    """设置专属头衔（仅群主可操作）
    
    Args:
        user_qq (str): 目标用户的QQ号
        title (str): 新的专属头衔，留空则删除头衔
        report (str): 设置理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"设置头衔功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SET_TITLE"):
        return "设置头衔功能未开启，无法执行此操作"
    
    # 权限检查 - 设置头衔需要群主权限
    can_operate, msg = await check_permission(
        _ctx, group_id, user_qq,
        PermissionLevel.OWNER, "设置专属头衔", requester_qq
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_special_title(
            group_id=group_id,
            user_id=int(user_qq),
            special_title=title,
            duration=-1  # 永久
        )
        
        action = f"设置为 '{title}'" if title else "清空"
        result = f"已将用户 {user_qq} 的专属头衔{action}"
        
        await send_admin_report(_ctx, "设置专属头衔", f"目标: {user_qq}\n新头衔: {title or '(空)'}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"设置专属头衔失败: {e}")
        return f"设置专属头衔失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_设置管理员",
    description="设置或取消群管理员（仅群主可操作）。权限检查模式下需提供requester_qq参数。",
)
async def admin_set_admin(_ctx: AgentCtx, user_qq: str, enable: bool, report: str, requester_qq: Optional[str] = None) -> str:
    """设置或取消管理员（仅群主可操作）
    
    Args:
        user_qq (str): 目标用户的QQ号
        enable (bool): True设置为管理员，False取消管理员
        report (str): 操作理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"设置管理员功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SET_ADMIN"):
        return "设置管理员功能未开启，无法执行此操作"
    
    # 权限检查 - 设置管理员需要群主权限
    can_operate, msg = await check_permission(
        _ctx, group_id, user_qq,
        PermissionLevel.OWNER, "设置管理员", requester_qq
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_admin(
            group_id=group_id,
            user_id=int(user_qq),
            enable=enable
        )
        
        action = "设置为管理员" if enable else "取消管理员"
        result = f"已将用户 {user_qq} {action}"
        
        await send_admin_report(_ctx, "设置管理员", f"目标: {user_qq}\n操作: {action}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"设置管理员失败: {e}")
        return f"设置管理员失败: {e}"


# ============== 消息管理功能 ==============

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_撤回消息",
    description="撤回指定的消息。权限检查模式下需提供requester_qq参数。",
)
async def admin_delete_message(_ctx: AgentCtx, message_id: str, report: str, requester_qq: Optional[str] = None) -> str:
    """撤回消息（需要管理员及以上权限）
    
    Args:
        message_id (str): 要撤回的消息ID
        report (str): 撤回理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"撤回消息功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_DELETE_MSG"):
        return "撤回消息功能未开启，无法执行此操作"
    
    # 撤回消息只检查操作者权限
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.ADMIN, "撤回消息"
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().delete_msg(message_id=int(message_id))
        
        result = f"已撤回消息 {message_id}"
        
        await send_admin_report(_ctx, "撤回消息", f"消息ID: {message_id}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"撤回消息失败: {e}")
        return f"撤回消息失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_设置精华消息",
    description="将消息设置为群精华。权限检查模式下需提供requester_qq参数。",
)
async def admin_set_essence(_ctx: AgentCtx, message_id: str, report: str, requester_qq: Optional[str] = None) -> str:
    """设置精华消息（需要管理员及以上权限）
    
    Args:
        message_id (str): 要设为精华的消息ID
        report (str): 设置理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"设置精华功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SET_ESSENCE"):
        return "设置精华功能未开启，无法执行此操作"
    
    # 设置精华只检查操作者权限
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.ADMIN, "设置精华消息"
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_essence_msg(message_id=int(message_id))
        
        result = f"已将消息 {message_id} 设为精华"
        
        await send_admin_report(_ctx, "设置精华", f"消息ID: {message_id}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"设置精华失败: {e}")
        return f"设置精华失败: {e}"


# ============== 群设置功能 ==============

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_修改群名称",
    description="修改群名称（仅群主可操作）。权限检查模式下需提供requester_qq参数。",
)
async def admin_set_group_name(_ctx: AgentCtx, name: str, report: str, requester_qq: Optional[str] = None) -> str:
    """修改群名称（仅群主可操作）
    
    Args:
        name (str): 新的群名称
        report (str): 修改理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"修改群名功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SET_GROUP_NAME"):
        return "修改群名称功能未开启，无法执行此操作"
    
    # 修改群名需要群主权限
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.OWNER, "修改群名称"
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_name(group_id=group_id, group_name=name)
        
        result = f"已将群名称修改为 '{name}'"
        
        await send_admin_report(_ctx, "修改群名称", f"新群名: {name}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"修改群名称失败: {e}")
        return f"修改群名称失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_修改群头像",
    description="修改群头像（仅群主可操作）。权限检查模式下需提供requester_qq参数。",
)
async def admin_set_group_portrait(_ctx: AgentCtx, file: str, report: str, requester_qq: Optional[str] = None) -> str:
    """修改群头像（仅群主可操作）
    
    Args:
        file (str): 图片文件路径或URL
        report (str): 修改理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"修改群头像功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SET_GROUP_PORTRAIT"):
        return "修改群头像功能未开启，无法执行此操作"
    
    # 修改群头像需要群主权限
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.OWNER, "修改群头像"
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot().set_group_portrait(group_id=group_id, file=file)
        
        result = "已修改群头像"
        
        await send_admin_report(_ctx, "修改群头像", f"图片: {file}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"修改群头像失败: {e}")
        return f"修改群头像失败: {e}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_发布群公告",
    description="发布群公告（需要管理员及以上权限）。权限检查模式下需提供requester_qq参数。",
)
async def admin_send_group_notice(_ctx: AgentCtx, content: str, report: str, requester_qq: Optional[str] = None) -> str:
    """发布群公告（需要管理员及以上权限）
    
    Args:
        content (str): 公告内容
        report (str): 发布理由
        requester_qq (str, optional): 请求者的QQ号，权限检查模式下必须提供
        
    Returns:
        str: 操作结果
    """
    chat_type, chat_id = parse_chat_key(_ctx)
    
    if chat_type != ChatType.GROUP.value:
        return f"发布群公告功能仅支持群聊，当前频道类型: {chat_type}"
    
    group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 检查功能开关
    if not effective_config.get("ENABLE_SEND_NOTICE"):
        return "发布群公告功能未开启，无法执行此操作"
    
    # 发布群公告需要管理员权限
    can_operate, msg = await check_requester_permission(
        group_id, requester_qq, PermissionLevel.ADMIN, "发布群公告"
    )
    if not can_operate:
        return msg
    
    try:
        await get_bot()._send_group_notice(group_id=group_id, content=content)
        
        result = "已发布群公告"
        
        await send_admin_report(_ctx, "发布群公告", f"内容: {content}\n理由: {report}")
        core.logger.info(f"[群{chat_id}] {result}，内容: {content}，理由: {report}")
        
        return result
    except Exception as e:
        core.logger.error(f"发布群公告失败: {e}")
        return f"发布群公告失败: {e}"


# ============== 分群配置管理功能 ==============

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="群管_查看群配置",
    description="查看当前群或指定群的群管配置。包括权限模式、功能开关等配置项。",
)
async def admin_view_group_config(
    _ctx: AgentCtx,
    group_id: Optional[int] = None
) -> str:
    """查看群配置
    
    Args:
        group_id: 群号，如果不提供则查看当前群
        
    Returns:
        str: 配置信息
    """
    # 如果没有指定群号，使用当前群
    if group_id is None:
        chat_type, chat_id = parse_chat_key(_ctx)
        if chat_type != ChatType.GROUP.value:
            return "查看群配置仅支持群聊"
        group_id = int(chat_id)
    
    # 获取该群的有效配置
    effective_config = await get_effective_config(group_id)
    
    # 获取该群的单独配置
    all_configs = await group_config_manager.list_group_configs()
    group_key = str(group_id)
    has_custom_config = group_key in all_configs
    
    # 格式化输出
    result = f"=== 群{group_id}的群管配置 ===\n\n"
    
    if has_custom_config:
        result += "【配置状态】使用分群配置（优先级高于全局配置）\n"
        custom_config = all_configs[group_key]
        result += f"【分群配置项】共 {len(custom_config)} 项\n"
    else:
        result += "【配置状态】使用全局默认配置（无单独配置）\n"
    
    result += "\n【当前有效配置】\n"
    result += f"  权限模式: {effective_config.get('PERMISSION_MODE', '未设置')}\n"
    result += f"  最大禁言时长: {effective_config.get('MAX_MUTE_DURATION', 0) // 86400} 天\n"
    result += f"  启用管理操作报告: {'是' if effective_config.get('ENABLE_ADMIN_REPORT') else '否'}\n"
    
    result += "\n【功能开关】\n"
    result += f"  允许禁言: {'✓' if effective_config.get('ENABLE_MUTE') else '✗'}\n"
    result += f"  允许全体禁言: {'✓' if effective_config.get('ENABLE_MUTE_ALL') else '✗'}\n"
    result += f"  允许踢人: {'✓' if effective_config.get('ENABLE_KICK') else '✗'}\n"
    result += f"  允许踢出并拉黑: {'✓' if effective_config.get('ENABLE_KICK_AND_BAN') else '✗'}\n"
    result += f"  允许修改群昵称: {'✓' if effective_config.get('ENABLE_SET_CARD') else '✗'}\n"
    result += f"  允许设置头衔: {'✓' if effective_config.get('ENABLE_SET_TITLE') else '✗'}\n"
    result += f"  允许设置管理员: {'✓' if effective_config.get('ENABLE_SET_ADMIN') else '✗'}\n"
    result += f"  允许撤回消息: {'✓' if effective_config.get('ENABLE_DELETE_MSG') else '✗'}\n"
    result += f"  允许设置精华: {'✓' if effective_config.get('ENABLE_SET_ESSENCE') else '✗'}\n"
    result += f"  允许修改群名称: {'✓' if effective_config.get('ENABLE_SET_GROUP_NAME') else '✗'}\n"
    result += f"  允许修改群头像: {'✓' if effective_config.get('ENABLE_SET_GROUP_PORTRAIT') else '✗'}\n"
    result += f"  允许发布群公告: {'✓' if effective_config.get('ENABLE_SEND_NOTICE') else '✗'}\n"
    
    protected_users = effective_config.get('PROTECTED_USERS', [])
    if protected_users:
        result += f"\n【受保护用户】({len(protected_users)}人)\n"
        for qq in protected_users[:10]:
            result += f"  - {qq}\n"
        if len(protected_users) > 10:
            result += f"  ...还有 {len(protected_users) - 10} 人\n"
    
    if has_custom_config:
        result += f"\n【分群配置详情】\n"
        for key, value in custom_config.items():
            result += f"  {key}: {value}\n"
    
    return result


# ============== 动态收集可用方法 ==============

@plugin.mount_collect_methods()
async def collect_available_methods(_ctx: AgentCtx):
    """根据 ALLOW_GROUPS 配置动态收集可用的群管方法

    如果 ALLOW_GROUPS 为空，则所有方法都可用
    如果 ALLOW_GROUPS 不为空，则只有配置的群可以使用群管方法
    """
    # 获取最新的配置
    admin_config = get_admin_config()
    
    # 如果 ALLOW_GROUPS 为空，所有方法都可用
    if len(admin_config.ALLOW_GROUPS) == 0:
        return plugin.sandbox_methods  # 返回所有已注册的方法

    # 获取当前群 ID
    chat_type, chat_id = parse_chat_key(_ctx)

    if chat_type != ChatType.GROUP.value:
        # 非群聊，不返回任何方法
        return []

    group_id = chat_id

    # 检查当前群是否在允许列表中
    if str(group_id) in admin_config.ALLOW_GROUPS:
        return plugin.sandbox_methods  # 在允许列表中，所有方法都可用

    # 不在允许列表中，返回空列表
    return []


# ============== 初始化和清理方法 ==============

@plugin.mount_init_method()
async def init():
    """插件初始化"""
    pass


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    # 此插件不需要清理任何资源
    pass
