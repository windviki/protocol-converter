# Protocol Converter - 通用协议转换系统

一个基于Jinja2模板的通用协议转换系统，支持多协议族之间的灵活转换。

## 功能特性

- **多协议族支持**: 支持A、B、C等多个协议族，每个协议族可包含数千个子协议
- **智能匹配**: 自动匹配输入JSON与协议模板，找到最合适的转换路径
- **变量提取**: 自动从输入数据中提取变量，支持普通变量和特殊变量
- **模板渲染**: 使用Jinja2模板引擎进行灵活的内容渲染
- **特殊变量处理**: 支持以__开头的特殊变量，可通过自定义函数进行处理
- **数据库存储**: 使用SQLAlchemy进行协议模板的持久化存储
- **命令行界面**: 提供完整的CLI工具，方便集成和使用

## 系统架构

```
protocol_converter/
├── core/              # 核心转换逻辑
│   └── converter.py   # 主转换器类
├── models/            # 数据模型
│   └── models.py      # SQLAlchemy模型定义
├── database/          # 数据库操作
│   ├── connection.py  # 数据库连接
│   └── manager.py     # 数据库管理
├── protocols/         # 协议加载
│   └── loader.py      # 协议文件加载器
├── converters/        # 转换函数
│   └── functions.py   # 特殊变量处理函数
├── utils/             # 工具函数
│   └── json_utils.py  # JSON处理工具
├── protocol_manager/  # 协议管理
│   └── manager.py     # 协议管理器
└── cli/               # 命令行界面
    └── main.py        # CLI主程序
```

## 安装和使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python cli.py init-db
```

### 3. 加载协议文件

```bash
python cli.py load -d ./examples/protocols
```

### 4. 转换协议

```bash
# 将A协议转换为C协议
python cli.py convert -s A -t C -i ./examples/input/A-1-input.json -o output.json

# 将A协议转换为B协议
python cli.py convert -s A -t B -i ./examples/input/A-1-input.json
```

### 5. 查看协议信息

```bash
# 列出所有协议族
python cli.py list-families

# 列出指定协议族的协议
python cli.py list-protocols -f A

# 查看协议详情
python cli.py show A-1
```

## 协议模板格式

### A协议族示例 (A-1.json)
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

### B协议族示例 (B-1.json)
```json
{
	"name": "Phone_Call",
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

### C协议族示例 (C-1.json)
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

## 变量类型

### 普通变量
- 格式: `{{ variable_name }}`
- 示例: `{{ phone_type }}`, `{{ person }}`
- 处理方式: 直接从输入数据中提取对应值进行替换

### 特殊变量
- 格式: `{{ __variable_name }}`
- 示例: `{{ __sid }}`, `{{ __priority }}`
- 处理方式: 调用对应的转换函数 `func_variable_name()` 进行处理

## 转换函数

系统提供以下内置转换函数：

### func_sid
处理__sid特殊变量，根据源协议和目标协议返回不同的标识符。

### func_label
处理__label特殊变量，返回协议特定的标签。

### func_priority
处理__priority特殊变量，根据服务类型和操作确定优先级。

### func_timestamp
处理__timestamp特殊变量，生成时间戳。

### func_session_id
处理__session_id特殊变量，生成会话ID。

### func_device_type
处理__device_type特殊变量，根据电话类型推断设备类型。

## 自定义转换函数

您可以添加自定义转换函数：

```python
from protocol_converter.converters.functions import register_converter_function

def func_custom(source_protocol, target_protocol, source_json, variables):
    # 自定义逻辑
    return "custom_value"

register_converter_function("func_custom", func_custom)
```

## 示例转换

### 输入数据 (A协议)
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

### 转换结果 (C协议)
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

## 扩展性

系统设计具有良好的扩展性：

1. **新协议族**: 只需按照现有格式创建新的协议文件即可
2. **新转换函数**: 可以轻松添加新的特殊变量处理函数
3. **新匹配算法**: 可以扩展协议匹配逻辑
4. **新存储后端**: 支持更换数据库或存储系统

## 性能考虑

- 协议模板缓存: 避免重复解析和加载
- 数据库索引: 优化查询性能
- 批量处理: 支持大规模协议文件的处理
- 内存管理: 合理使用缓存和清理机制

## 许可证

MIT License