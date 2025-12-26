"""
群管插件 - 分群配置管理模块

提供分群配置的读取、写入、合并等功能。
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

from nekro_agent.api import core


class GroupConfigManager:
    """分群配置管理器
    
    管理各群单独的群管配置，支持与全局配置合并。
    """

    def __init__(self, config_file_path: str = "data/group_configs.json"):
        """初始化配置管理器
        
        Args:
            config_file_path: 配置文件路径
        """
        self.config_file_path = Path(config_file_path)
        self._config_cache: dict[str, dict] = {}
        self._effective_cache: dict[int, dict] = {}  # 有效配置缓存
        self._cache_ttl = 60  # 缓存有效期（秒）
        self._cache_timestamps: dict[int, float] = {}
        self._ensure_config_file()

    def _ensure_config_file(self) -> None:
        """确保配置文件存在"""
        # 确保目录存在
        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果文件不存在，创建空配置
        if not self.config_file_path.exists():
            self._save_config({})
            core.logger.info(f"[群管配置] 创建配置文件: {self.config_file_path}")

    def _load_config(self) -> dict[str, dict]:
        """加载配置文件
        
        Returns:
            配置字典
        """
        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                core.logger.debug(f"[群管配置] 加载配置成功，共 {len(config)} 个群有单独配置")
                return config
        except FileNotFoundError:
            core.logger.warning(f"[群管配置] 配置文件不存在，返回空配置")
            return {}
        except json.JSONDecodeError as e:
            core.logger.error(f"[群管配置] 配置文件格式错误: {e}")
            return {}
        except Exception as e:
            core.logger.error(f"[群管配置] 加载配置失败: {e}")
            return {}

    def _save_config(self, config: dict[str, dict]) -> bool:
        """保存配置文件
        
        Args:
            config: 配置字典
            
        Returns:
            是否保存成功
        """
        try:
            with open(self.config_file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            core.logger.info(f"[群管配置] 保存配置成功")
            return True
        except Exception as e:
            core.logger.error(f"[群管配置] 保存配置失败: {e}")
            return False

    async def get_group_config(
        self,
        group_id: int,
        global_config: dict[str, Any]
    ) -> dict[str, Any]:
        """获取指定群的有效配置（合并全局配置和分群配置，带缓存）
        
        Args:
            group_id: 群号
            global_config: 全局配置
            
        Returns:
            合并后的配置字典
        """
        # 检查缓存是否有效
        current_time = time.time()
        if group_id in self._effective_cache:
            cache_time = self._cache_timestamps.get(group_id, 0)
            if current_time - cache_time < self._cache_ttl:
                core.logger.debug(f"[群管配置] 群{group_id}使用缓存配置")
                return self._effective_cache[group_id]
        
        group_key = str(group_id)
        
        # 加载最新配置
        all_configs = self._load_config()
        group_config = all_configs.get(group_key, {})
        
        # 合并配置：分群配置优先
        merged_config = {**global_config, **group_config}
        
        # 更新缓存
        self._effective_cache[group_id] = merged_config
        self._cache_timestamps[group_id] = current_time
        
        core.logger.debug(
            f"[群管配置] 群{group_id}配置: "
            f"全局配置项={len(global_config)}, "
            f"分群配置项={len(group_config)}, "
            f"合并后={len(merged_config)}"
        )
        
        return merged_config
    
    def clear_cache(self, group_id: Optional[int] = None) -> None:
        """清除配置缓存
        
        Args:
            group_id: 群号，如果为 None 则清除所有缓存
        """
        if group_id is None:
            self._effective_cache.clear()
            self._cache_timestamps.clear()
            core.logger.debug("[群管配置] 已清除所有配置缓存")
        else:
            self._effective_cache.pop(group_id, None)
            self._cache_timestamps.pop(group_id, None)
            core.logger.debug(f"[群管配置] 已清除群{group_id}的配置缓存")

    async def set_group_config(
        self,
        group_id: int,
        config_key: str,
        config_value: Any
    ) -> bool:
        """设置指定群的配置项
        
        Args:
            group_id: 群号
            config_key: 配置键
            config_value: 配置值
            
        Returns:
            是否设置成功
        """
        group_key = str(group_id)
        
        # 加载现有配置
        all_configs = self._load_config()
        
        # 确保该群的配置字典存在
        if group_key not in all_configs:
            all_configs[group_key] = {}
        
        # 设置配置值
        all_configs[group_key][config_key] = config_value
        
        # 保存配置
        success = self._save_config(all_configs)
        
        if success:
            core.logger.info(f"[群管配置] 群{group_id}设置配置: {config_key}={config_value}")
        
        return success

    async def set_multiple_group_config(
        self,
        group_id: int,
        config_dict: dict[str, Any]
    ) -> bool:
        """批量设置指定群的配置项
        
        Args:
            group_id: 群号
            config_dict: 配置字典
            
        Returns:
            是否设置成功
        """
        group_key = str(group_id)
        
        # 加载现有配置
        all_configs = self._load_config()
        
        # 确保该群的配置字典存在
        if group_key not in all_configs:
            all_configs[group_key] = {}
        
        # 批量设置配置值
        all_configs[group_key].update(config_dict)
        
        # 保存配置
        success = self._save_config(all_configs)
        
        if success:
            core.logger.info(f"[群管配置] 群{group_id}批量设置配置: {len(config_dict)}项")
        
        return success

    async def delete_group_config(
        self,
        group_id: int,
        config_key: Optional[str] = None
    ) -> bool:
        """删除指定群的配置项
        
        Args:
            group_id: 群号
            config_key: 配置键，如果为None则删除该群的所有配置
            
        Returns:
            是否删除成功
        """
        group_key = str(group_id)
        
        # 加载现有配置
        all_configs = self._load_config()
        
        if group_key not in all_configs:
            core.logger.warning(f"[群管配置] 群{group_id}没有单独配置，无需删除")
            return True
        
        if config_key is None:
            # 删除该群的所有配置
            del all_configs[group_key]
            core.logger.info(f"[群管配置] 删除群{group_id}的所有配置")
        else:
            # 删除指定配置项
            if config_key in all_configs[group_key]:
                del all_configs[group_key][config_key]
                core.logger.info(f"[群管配置] 删除群{group_id}的配置项: {config_key}")
                
                # 如果该群没有配置项了，删除该群
                if not all_configs[group_key]:
                    del all_configs[group_key]
            else:
                core.logger.warning(f"[群管配置] 群{group_id}没有配置项: {config_key}")
                return True
        
        # 保存配置
        return self._save_config(all_configs)

    async def list_group_configs(self) -> dict[str, dict]:
        """列出所有有单独配置的群
        
        Returns:
            群配置字典 {group_id: config_dict}
        """
        all_configs = self._load_config()
        return all_configs

    async def reset_group_config(self, group_id: int) -> bool:
        """重置指定群的配置为全局配置（删除该群的单独配置）
        
        Args:
            group_id: 群号
            
        Returns:
            是否重置成功
        """
        return await self.delete_group_config(group_id)

    async def get_config_summary(self, group_id: int) -> str:
        """获取指定群的配置摘要
        
        Args:
            group_id: 群号
            
        Returns:
            配置摘要字符串
        """
        all_configs = self._load_config()
        group_key = str(group_id)
        
        if group_key not in all_configs:
            return f"群{group_id}使用全局默认配置（无单独配置）"
        
        config = all_configs[group_key]
        items = [f"{k}={v}" for k, v in config.items()]
        return f"群{group_id}单独配置（共{len(config)}项）:\n" + "\n".join(f"  - {item}" for item in items)
