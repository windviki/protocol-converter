# Protocol Converter - 通用协议转换系统

一个基于Jinja2模板的通用协议转换系统，采用模块化架构和丰富的上下文支持，支持多协议族之间的灵活转换。

## ✨ 核心特性

- **🏗️ 模块化架构**: 清晰的职责分离，每个模块专注特定功能
- **📊 丰富上下文**: 统一的ConversionContext提供协议信息、数组元数据、进度追踪等
- **🔄 动态数组处理**: 高级数组处理支持，每个元素都有独立的上下文信息
- **🎯 智能匹配**: 自动匹配输入JSON与协议模板，找到最合适的转换路径
- **🔧 灵活变量**: 支持普通变量和特殊变量，统一基于上下文的处理方式
- **🗄️ 数据库存储**: 使用SQLAlchemy进行协议模板的持久化存储
- **💻 命令行界面**: 提供完整的CLI工具，方便集成和使用

## 📁 系统架构

```
protocol_converter/
├── core/                      # 核心转换逻辑 (模块化)
│   ├── converter.py           # 主转换器类 (简化版)
│   ├── matcher.py             # 协议匹配逻辑
│   ├── extractor.py           # 变量提取引擎
│   └── renderer.py            # 模板渲染引擎
├── models/                    # 数据模型
│   ├── types.py               # 核心数据类 (ArrayMarker, ConversionContext等)
│   └── models.py              # SQLAlchemy模型定义
├── converters/                # 转换函数
│   └── functions.py           # 统一上下文转换函数
├── database/                  # 数据库操作
│   ├── connection.py          # 数据库连接
│   └── manager.py             # 数据库管理
├── protocols/                 # 协议加载
│   └── loader.py              # 协议文件加载器
├── protocol_manager/          # 协议管理
│   └── manager.py             # 协议管理器
├── utils/                     # 工具函数
│   └── json_utils.py          # JSON处理工具
└── cli/                       # 命令行界面
    └── main.py                # CLI主程序
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python cli.py init-db

# 加载协议文件
python cli.py load -d ./examples/protocols
```

### 2. 基础转换

```bash
# 将A协议转换为C协议
python cli.py convert -s A -t C -i ./examples/input/A-1-input.json -o output.json

# 将A协议转换为B协议
python cli.py convert -s A -t B -i ./examples/input/A-1-input.json
```

### 3. 协议管理

```bash
# 列出所有协议族
python cli.py list-families

# 列出指定协议族的协议
python cli.py list-protocols -f A

# 查看协议详情
python cli.py show A-1
```

### 4. 测试验证

```bash
# 运行基础系统测试
python test_system.py

# 运行统一上下文测试 (ConversionContext功能)
python test_unified_context.py

# 运行动态数组测试
python test_array_context.py

# 或使用make命令
make test
```

## 📋 协议模板格式

### 基础协议示例

#### A协议族示例 (A-1.json)
```json
{
	"domain": "telephone",
	"action": "DIAL",
	"slots": {
		"category": "{{ phone_type }}",
		"name": "{{ person }}",
		"raw_name": "{{ person }}"
	}
}
```

#### C协议族示例 (C-1.json)
```json
{
	"tao": "phone.contact.call",
	"slots": [
		{
			"name": "PERSON",
			"value": "{{ person }}",
			"label": "O"
		},
		{
			"name": "PHONE_TYPE",
			"value": "{{ phone_type }}",
			"label": "{{ __sid }}"
		}
	]
}
```

### 动态数组支持

#### TestA协议族 (带动态数组)
```json
{
	"operation": "process",
	"data": [
		"{# array_dynamic: true #}",
		{
			"name": "{{ name }}",
			"value": "{{ value }}",
			"type": "{{ type }}",
			"domain": "{{ domain }}"
		}
	]
}
```

#### TestC协议族 (增强上下文支持)
```json
{
	"operation": "transform",
	"items": [
		"{# array_dynamic: true #}",
		{
			"title": "{{ name | capitalize }}",
			"amount": "{{ value }}",
			"metadata": {
				"index": "{{ __array_index }}",
				"total": "{{ __array_total }}",
				"progress": "{{ __progress }}",
				"session_id": "{{ __session_id }}",
				"is_last": "{{ __is_last_item }}"
			}
		}
	]
}
```

## 🔧 变量类型

### 普通变量
- **格式**: `{{ variable_name }}`
- **示例**: `{{ phone_type }}`, `{{ person }}`
- **处理方式**: 直接从输入数据的对应字段中提取值进行替换

### 特殊变量 (统一上下文)
- **格式**: `{{ __variable_name }}`
- **示例**: `{{ __session_id }}`, `{{ __array_index }}`, `{{ __progress }}`
- **处理方式**: 调用统一的转换函数 `func_variable_name(context: ConversionContext)`

## 🛠️ 转换函数

系统提供以下内置转换函数，所有函数都使用统一的ConversionContext签名：

### 基础转换函数
- **func_sid**: 根据`context.source_protocol`和`context.target_protocol`返回不同的标识符
- **func_label**: 返回协议特定的标签
- **func_priority**: 根据服务类型和操作确定优先级
- **func_timestamp**: 生成时间戳
- **func_device_type**: 根据电话类型推断设备类型

### 数组相关函数
- **func_array_index**: 返回当前数组元素的索引 (`context.array_index`)
- **func_array_total**: 返回数组总长度 (`context.array_total`)
- **func_progress**: 返回处理进度信息，如 "2/3 (66.7%)"
- **func_is_last_item**: 判断是否为最后一个项目 (`"true"`/`"false"`)

### 上下文信息函数
- **func_session_id**: 基于上下文生成会话ID，数组中每个元素都有不同的ID
- **func_session_id_v2**: 增强版session_id，包含完整的上下文信息
- **func_conversion_id**: 返回转换会话ID (`context.conversion_id`)
- **func_current_path**: 返回当前渲染路径 (`context.current_path`)
- **func_source_protocol**: 返回源协议名称
- **func_target_protocol**: 返回目标协议名称
- **func_render_depth**: 返回渲染深度
- **func_parent_path**: 返回父级路径

### 💡 创建自定义转换函数

```python
from models.types import ConversionContext

def func_custom(context: ConversionContext) -> str:
    """
    自定义转换函数示例
    """
    # 访问丰富的上下文信息
    if context.is_array_context():
        # 在数组中的处理
        index = context.array_index
        total = context.array_total
        progress = context.get_progress_info()
        return f"custom_item_{index}_of_{total}_({progress['percentage']:.1f}%)"

    # 普通处理
    return f"custom_{context.source_protocol}_to_{context.target_protocol}"

# 注册到CONVERTER_FUNCTIONS字典
CONVERTER_FUNCTIONS["func_custom"] = func_custom
```

### 🎯 上下文信息访问

```python
def func_example(context: ConversionContext) -> str:
    # 获取协议信息
    source_id = context.source_protocol_id
    target_id = context.target_protocol_id

    # 获取数组信息
    if context.is_array_context():
        array_path = context.array_path
        current_element = context.current_element

    # 获取进度信息
    progress = context.get_progress_info()

    # 获取源数据字段
    domain = context.get_source_field("domain", "unknown")

    # 添加调试信息
    context.add_debug_info("custom_processing", True)

    return f"processed_{domain}_{progress['current']}"
```

## 📝 示例转换

### 基础转换示例

#### 输入数据 (A协议)
```json
{
	"domain": "telephone",
	"action": "DIAL",
	"slots": {
		"category": "手机",
		"name": "张三",
		"raw_name": "张三"
	}
}
```

#### 转换结果 (C协议)
```json
{
	"tao": "phone.contact.call",
	"slots": [
		{
			"name": "PERSON",
			"value": "张三",
			"label": "O"
		},
		{
			"name": "PHONE_TYPE",
			"value": "手机",
			"label": "PHONE_TYPE_MOBILE"
		}
	]
}
```

### 动态数组转换示例

#### 输入数据 (带数组)
```json
{
	"operation": "process",
	"data": [
		{
			"name": "alice",
			"value": 100,
			"type": "primary",
			"domain": "test"
		},
		{
			"name": "bob",
			"value": 200,
			"type": "secondary",
			"domain": "test"
		},
		{
			"name": "charlie",
			"value": 300,
			"type": "primary",
			"domain": "test"
		}
	]
}
```

#### 转换结果 (每个元素有不同上下文信息)
```json
{
	"operation": "transform",
	"items": [
		{
			"title": "Alice",
			"amount": "100",
			"metadata": {
				"index": "0",
				"total": "3",
				"progress": "1/3 (33.3%)",
				"session_id": "item0_convconv_a1b_2f7c9f",
				"is_last": "false"
			}
		},
		{
			"title": "Bob",
			"amount": "200",
			"metadata": {
				"index": "1",
				"total": "3",
				"progress": "2/3 (66.7%)",
				"session_id": "item1_convconv_b2c_9a3d1e",
				"is_last": "false"
			}
		},
		{
			"title": "Charlie",
			"amount": "300",
			"metadata": {
				"index": "2",
				"total": "3",
				"progress": "3/3 (100.0%)",
				"session_id": "item2_convconv_c3d_8f4b2a",
				"is_last": "true"
			}
		}
	]
}
```

## 💻 代码使用示例

### 基础转换
```python
from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS

# 创建转换器
converter = ProtocolConverter(CONVERTER_FUNCTIONS)

# 加载协议模板
converter.load_protocol("A-1", "A", a_template)
converter.load_protocol("C-1", "C", c_template)

# 执行转换
result = converter.convert("A", "C", input_data)

if result.success:
    print(f"转换成功: {result.result}")
else:
    print(f"转换失败: {result.error}")
```

### 自定义转换函数
```python
from models.types import ConversionContext
from converters.functions import CONVERTER_FUNCTIONS

def func_order_id(context: ConversionContext) -> str:
    """生成订单ID，数组元素有不同的ID"""
    if context.is_array_context():
        return f"ORDER_{context.array_index + 1:04d}_{context.conversion_id[:8]}"
    return f"ORDER_SINGLE_{context.conversion_id[:8]}"

# 注册函数
CONVERTER_FUNCTIONS["func_order_id"] = func_order_id
```

## 🚀 扩展性

系统设计具有出色的扩展性：

### 1. 新协议族
- 按照标准格式创建新的协议文件
- 支持动态数组标记
- 可充分利用特殊变量功能

### 2. 新转换函数
- 使用统一的ConversionContext签名
- 访问丰富的上下文信息
- 支持复杂的业务逻辑

### 3. 自定义匹配算法
- 扩展ProtocolMatcher类
- 实现专门的匹配逻辑
- 添加协议验证功能

### 4. 增强上下文处理
- 访问数组元数据: `context.array_index`, `context.array_total`
- 追踪处理进度: `context.get_progress_info()`
- 调试信息收集: `context.add_debug_info()`

## ⚡ 性能优化

- **模块化缓存**: 各模块独立缓存优化
- **协议模板缓存**: 避免重复解析和加载
- **数据库索引**: 优化查询性能
- **批量处理**: 支持大规模协议文件处理
- **内存管理**: 合理使用缓存和清理机制
- **上下文复用**: 高效的上下文信息传递

## 🔄 向后兼容性

- **功能完全兼容**: 所有现有功能完全保留
- **协议模板**: 原有协议模板继续正常工作
- **API接口**: 核心API保持不变
- **渐进升级**: 可逐步迁移到新功能

## 📄 许可证

MIT License