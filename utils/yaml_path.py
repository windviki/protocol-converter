"""
YAML路径操作工具
提供精确的YAML数据路径定位和操作功能
"""

from typing import Any, List, Union, Dict, Optional, Iterable
import re
from dataclasses import dataclass

@dataclass
class PathSegment:
    """路径段数据结构"""
    type: str  # 'object_key', 'array_index', 'array_all', 'array_wildcard'
    value: Union[str, int]  # 具体值
    is_optional: bool = False  # 是否可选字段

class PathError(Exception):
    """路径操作错误"""
    pass

class YamlPath:
    """YAML路径操作器"""

    # 路径解析正则表达式
    PATH_PATTERN = re.compile(r'([^.\[\]]+|\[\d+\]|\[\*\]|\[-\d+\]|\[\w+\?\])')

    def __init__(self, path_str: str):
        """
        初始化YAML路径

        Args:
            path_str: 路径字符串，如 "slots.waypoints[0].name"
        """
        self.path_str = path_str
        self.segments = self._parse_path(path_str)
        self.is_absolute = path_str.startswith('.')

    def _parse_path(self, path_str: str) -> List[PathSegment]:
        """解析路径字符串为路径段列表"""
        segments = []
        matches = self.PATH_PATTERN.finditer(path_str)

        for match in matches:
            segment_str = match.group(1)

            if segment_str.startswith('[') and segment_str.endswith(']'):
                # 数组索引或通配符
                content = segment_str[1:-1]
                if content == '*':
                    segments.append(PathSegment('array_wildcard', '*'))
                elif content.startswith('-'):
                    # 负索引
                    try:
                        segments.append(PathSegment('array_index', int(content)))
                    except ValueError:
                        raise PathError(f"Invalid array index: {segment_str}")
                elif content.endswith('?'):
                    # 可选字段
                    key = content[:-1]
                    segments.append(PathSegment('object_key', key, is_optional=True))
                else:
                    # 正索引
                    try:
                        segments.append(PathSegment('array_index', int(content)))
                    except ValueError:
                        raise PathError(f"Invalid array index: {segment_str}")
            else:
                # 对象键
                is_optional = segment_str.endswith('?')
                key = segment_str[:-1] if is_optional else segment_str
                segments.append(PathSegment('object_key', key, is_optional))

        return segments

    def get_value(self, data: Any) -> Any:
        """
        根据路径获取数据值

        Args:
            data: 数据对象

        Returns:
            路径对应的值

        Raises:
            PathError: 路径不存在或无效
        """
        current = data

        for i, segment in enumerate(self.segments):
            try:
                if segment.type == 'object_key':
                    if not isinstance(current, dict):
                        raise PathError(f"Expected dict at segment {i}, got {type(current).__name__}")

                    if segment.value not in current:
                        if segment.is_optional:
                            return None
                        raise PathError(f"Key '{segment.value}' not found at segment {i}")

                    current = current[segment.value]

                elif segment.type == 'array_index':
                    if not isinstance(current, list):
                        raise PathError(f"Expected list at segment {i}, got {type(current).__name__}")

                    # 处理负索引
                    index = segment.value if segment.value >= 0 else len(current) + segment.value

                    if index < 0 or index >= len(current):
                        raise PathError(f"Array index {index} out of bounds at segment {i}")

                    current = current[index]

                elif segment.type == 'array_wildcard':
                    if not isinstance(current, list):
                        raise PathError(f"Expected list at segment {i}, got {type(current).__name__}")

                    # 通配符：返回所有元素的值
                    remaining_path = YamlPath.from_segments(self.segments[i+1:])
                    if remaining_path.segments:
                        # 还有后续路径段
                        return [remaining_path.get_value(item) for item in current]
                    else:
                        # 通配符是最后一段
                        return current

            except (KeyError, IndexError, TypeError) as e:
                if segment.is_optional:
                    return None
                raise PathError(f"Failed to navigate to '{segment.value}' at segment {i}: {str(e)}")

        return current

    def set_value(self, data: Any, value: Any) -> None:
        """
        根据路径设置数据值

        Args:
            data: 数据对象
            value: 要设置的值

        Raises:
            PathError: 路径无效
        """
        if not self.segments:
            raise PathError("Cannot set value on empty path")

        current = data

        # 导航到父级位置
        for i, segment in enumerate(self.segments[:-1]):
            if segment.type == 'object_key':
                if not isinstance(current, dict):
                    raise PathError(f"Expected dict at segment {i}, got {type(current).__name__}")

                if segment.value not in current:
                    # 创建中间结构
                    next_segment = self.segments[i+1]
                    if next_segment.type in ['array_index', 'array_wildcard']:
                        current[segment.value] = []
                    else:
                        current[segment.value] = {}

                current = current[segment.value]

            elif segment.type == 'array_index':
                if not isinstance(current, list):
                    raise PathError(f"Expected list at segment {i}, got {type(current).__name__}")

                # 确保数组长度足够
                while len(current) <= segment.value:
                    current.append(None)

                if current[segment.value] is None:
                    # 创建中间结构
                    next_segment = self.segments[i+1]
                    if next_segment.type in ['array_index', 'array_wildcard']:
                        current[segment.value] = []
                    else:
                        current[segment.value] = {}

                current = current[segment.value]

        # 设置最终值
        final_segment = self.segments[-1]
        if final_segment.type == 'object_key':
            if not isinstance(current, dict):
                raise PathError(f"Expected dict at parent segment, got {type(current).__name__}")
            current[final_segment.value] = value

        elif final_segment.type == 'array_index':
            if not isinstance(current, list):
                raise PathError(f"Expected list at parent segment, got {type(current).__name__}")

            # 确保数组长度足够
            while len(current) <= final_segment.value:
                current.append(None)

            current[final_segment.value] = value

    def exists(self, data: Any) -> bool:
        """
        检查路径是否存在

        Args:
            data: 数据对象

        Returns:
            True if path exists, False otherwise
        """
        try:
            self.get_value(data)
            return True
        except PathError:
            return False

    def delete(self, data: Any) -> bool:
        """
        删除路径对应的值

        Args:
            data: 数据对象

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.segments:
            return False

        try:
            parent_path = self.get_parent_path()
            parent_data = parent_path.get_value(data)

            final_segment = self.segments[-1]
            if final_segment.type == 'object_key' and isinstance(parent_data, dict):
                if final_segment.value in parent_data:
                    del parent_data[final_segment.value]
                    return True

            elif final_segment.type == 'array_index' and isinstance(parent_data, list):
                index = final_segment.value if final_segment.value >= 0 else len(parent_data) + final_segment.value
                if 0 <= index < len(parent_data):
                    parent_data.pop(index)
                    return True

        except (PathError, IndexError, KeyError):
            pass

        return False

    def get_parent_path(self) -> 'YamlPath':
        """
        获取父级路径

        Returns:
            父级路径对象

        Raises:
            PathError: 当前路径没有父级
        """
        if len(self.segments) <= 1:
            raise PathError("Root path has no parent")

        return YamlPath.from_segments(self.segments[:-1])

    def append(self, segment: str) -> 'YamlPath':
        """
        追加路径段

        Args:
            segment: 要追加的路径段

        Returns:
            新的路径对象
        """
        new_segments = self.segments.copy()
        new_segments.extend(YamlPath(segment).segments)

        new_path = YamlPath.__new__(YamlPath)
        new_path.segments = new_segments
        new_path.path_str = new_path._rebuild_path_string()
        new_path.is_absolute = self.is_absolute

        return new_path

    def prepend(self, segment: str) -> 'YamlPath':
        """
        在前面添加路径段

        Args:
            segment: 要添加的路径段

        Returns:
            新的路径对象
        """
        new_segments = YamlPath(segment).segments.copy()
        new_segments.extend(self.segments)

        new_path = YamlPath.__new__(YamlPath)
        new_path.segments = new_segments
        new_path.path_str = new_path._rebuild_path_string()
        new_path.is_absolute = self.is_absolute

        return new_path

    def normalize(self) -> 'YamlPath':
        """
        规范化路径（处理 . 和 .. 等）

        Returns:
            规范化后的路径对象
        """
        normalized_segments = []

        for segment in self.segments:
            if segment.type == 'object_key' and segment.value == '.':
                continue  # 跳过当前目录
            elif segment.type == 'object_key' and segment.value == '..':
                if normalized_segments:
                    normalized_segments.pop()  # 返回上级目录
            else:
                normalized_segments.append(segment)

        return YamlPath.from_segments(normalized_segments)

    def to_schema_path(self) -> str:
        """
        转换为schema路径格式

        Returns:
            schema路径字符串
        """
        parts = []
        for segment in self.segments:
            if segment.type == 'object_key':
                parts.append(segment.value)
            elif segment.type in ['array_index', 'array_wildcard']:
                parts.append('items')

        return '.'.join(parts)

    def match(self, pattern: str) -> bool:
        """
        检查路径是否匹配模式

        Args:
            pattern: 路径模式，支持通配符

        Returns:
            True if matches, False otherwise
        """
        pattern_segments = YamlPath(pattern).segments

        if len(self.segments) != len(pattern_segments):
            return False

        for seg, pat_seg in zip(self.segments, pattern_segments):
            if pat_seg.type == 'array_wildcard':
                continue  # 通配符匹配任何内容
            elif seg.type != pat_seg.type or seg.value != pat_seg.value:
                return False

        return True

    def get_common_ancestor(self, other: 'YamlPath') -> Optional['YamlPath']:
        """
        获取与另一个路径的共同祖先

        Args:
            other: 另一个路径

        Returns:
            共同祖先路径，如果没有则返回None
        """
        common_segments = []

        for seg1, seg2 in zip(self.segments, other.segments):
            if seg1.type == seg2.type and seg1.value == seg2.value:
                common_segments.append(seg1)
            else:
                break

        if common_segments:
            return YamlPath.from_segments(common_segments)
        return None

    def relative_to(self, base: 'YamlPath') -> 'YamlPath':
        """
        获取相对于基础路径的相对路径

        Args:
            base: 基础路径

        Returns:
            相对路径

        Raises:
            PathError: 无法计算相对路径
        """
        if self.segments[:len(base.segments)] != base.segments:
            raise PathError(f"Path '{self.path_str}' is not relative to '{base.path_str}'")

        relative_segments = self.segments[len(base.segments):]
        return YamlPath.from_segments(relative_segments)

    @classmethod
    def from_segments(cls, segments: List[PathSegment]) -> 'YamlPath':
        """从路径段创建YamlPath"""
        path_obj = cls.__new__(cls)
        path_obj.segments = segments
        path_obj.path_str = path_obj._rebuild_path_string()
        path_obj.is_absolute = False
        return path_obj

    @classmethod
    def join(cls, *paths: str) -> 'YamlPath':
        """连接多个路径段"""
        if not paths:
            return cls("")

        first_path = cls(paths[0])
        result_segments = first_path.segments.copy()

        for path_str in paths[1:]:
            path_obj = cls(path_str)
            result_segments.extend(path_obj.segments)

        return cls.from_segments(result_segments)

    def _rebuild_path_string(self) -> str:
        """重建路径字符串"""
        parts = []
        for segment in self.segments:
            if segment.type == 'object_key':
                key = segment.value
                if segment.is_optional:
                    key += '?'
                parts.append(key)
            elif segment.type == 'array_index':
                parts.append(f"[{segment.value}]")
            elif segment.type == 'array_wildcard':
                parts.append("[*]")

        return ".".join(parts)

    def __str__(self) -> str:
        return self.path_str

    def __repr__(self) -> str:
        return f"YamlPath('{self.path_str}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, YamlPath):
            return False
        return self.segments == other.segments

    def __hash__(self) -> int:
        return hash(tuple(self.segments))

    def __len__(self) -> int:
        return len(self.segments)

    def __getitem__(self, index: Union[int, slice]) -> Union[PathSegment, 'YamlPath']:
        if isinstance(index, int):
            return self.segments[index]
        else:
            return YamlPath.from_segments(self.segments[index])

# 便利函数
def parse_path(path_str: str) -> YamlPath:
    """解析路径字符串"""
    return YamlPath(path_str)

def join_paths(*paths: str) -> YamlPath:
    """连接多个路径"""
    return YamlPath.join(*paths)

def get_path_value(data: Any, path_str: str) -> Any:
    """获取路径值的便利函数"""
    path = YamlPath(path_str)
    return path.get_value(data)

def set_path_value(data: Any, path_str: str, value: Any) -> None:
    """设置路径值的便利函数"""
    path = YamlPath(path_str)
    path.set_value(data, value)

def path_exists(data: Any, path_str: str) -> bool:
    """检查路径是否存在的便利函数"""
    path = YamlPath(path_str)
    return path.exists(data)