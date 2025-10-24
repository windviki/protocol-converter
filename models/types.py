"""
Data types and models for protocol conversion system
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class ArrayMarker:
    """数组处理标记"""
    field_path: str  # 字段路径，如 "items"
    is_dynamic: bool  # 是否动态处理整个数组
    template_item: Dict[str, Any]  # 数组项的模板结构


@dataclass
class ProtocolTemplate:
    """协议模板数据类"""
    protocol_id: str
    protocol_family: str
    template_content: Dict[str, Any]
    variables: List[str]
    special_variables: List[str]
    array_markers: List[ArrayMarker]  # 数组处理标记列表


@dataclass
class ConversionResult:
    """转换结果数据类"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    matched_protocol: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ConversionContext:
    """转换上下文，为转换函数提供完整的信息"""
    # 基础转换信息
    source_protocol: str
    target_protocol: str
    source_json: Dict[str, Any]
    variables: Dict[str, Any]

    # 数组相关信息
    array_path: Optional[str] = None  # 当前数组路径，如 "items"
    array_index: Optional[int] = None  # 当前元素在数组中的索引
    array_total: Optional[int] = None  # 数组总长度
    current_element: Optional[Dict[str, Any]] = None  # 当前数组元素的数据

    # 渲染层级信息
    render_depth: int = 0  # 当前渲染深度
    parent_path: Optional[str] = None  # 父级路径
    current_path: Optional[str] = None  # 当前字段路径

    # 协议信息
    source_protocol_id: Optional[str] = None  # 源协议ID
    target_protocol_id: Optional[str] = None  # 目标协议ID
    protocol_family: Optional[str] = None  # 协议族

    # 数据统计信息
    total_input_items: int = 0  # 输入数据中的项目总数
    processed_items: int = 0  # 已处理的项目数量
    is_last_item: bool = False  # 是否为最后一个项目

    # 元数据
    timestamp: Optional[str] = None  # 转换时间戳
    conversion_id: Optional[str] = None  # 转换会话ID
    debug_info: Dict[str, Any] = None  # 调试信息

    def __post_init__(self):
        """初始化后处理"""
        if self.debug_info is None:
            self.debug_info = {}

        # 设置协议族信息
        if self.source_protocol and not self.protocol_family:
            self.protocol_family = self.source_protocol

        # 统计输入项目数量
        self._count_input_items()

        # 设置时间戳
        import datetime
        if not self.timestamp:
            self.timestamp = datetime.datetime.now().isoformat()

        # 生成转换ID
        import uuid
        if not self.conversion_id:
            self.conversion_id = f"conv_{uuid.uuid4().hex[:12]}"

        # 判断是否为最后一个项目
        if self.array_index is not None and self.array_total is not None:
            self.is_last_item = (self.array_index == self.array_total - 1)

    def _count_input_items(self):
        """统计输入数据中的项目数量"""
        if isinstance(self.source_json, dict):
            # 查找最大的数组
            for value in self.source_json.values():
                if isinstance(value, list):
                    self.total_input_items = max(self.total_input_items, len(value))

    def get_variable(self, name: str, default: Any = None) -> Any:
        """安全获取变量值"""
        return self.variables.get(name, default)

    def get_source_field(self, field_path: str, default: Any = None) -> Any:
        """从源数据中获取字段值"""
        parts = field_path.split('.')
        current = self.source_json
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def is_array_context(self) -> bool:
        """判断是否在数组上下文中"""
        return self.array_index is not None

    def get_progress_info(self) -> Dict[str, Any]:
        """获取处理进度信息"""
        current = self.array_index + 1 if self.array_index is not None else 0
        total = self.array_total or self.total_input_items
        percentage = (current / total * 100) if total > 0 else 0

        return {
            "current": current,
            "total": total,
            "percentage": percentage,
            "is_last": self.is_last_item
        }

    def add_debug_info(self, key: str, value: Any):
        """添加调试信息"""
        self.debug_info[key] = value