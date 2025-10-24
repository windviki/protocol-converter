# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

- 永远用中文回复我
- 每次重要修改需要在本地提交git
- python版本3.11
- 尊重工程的文件夹结构规范，不要随意放置文件：所有测试放置到tests/目录下

## Project Overview

This is a universal protocol conversion system based on Jinja2 templates with modular architecture and rich context support. The system supports flexible conversion between multiple protocol families (A, B, C) with intelligent protocol matching and powerful variable handling.

## Key Features

- **Modular Architecture**: Clean separation of concerns with dedicated modules for each function
- **Unified ConversionContext**: Rich context information passed to all converter functions
- **Dynamic Array Processing**: Advanced support for dynamic arrays with context-aware processing
- **Multi-protocol family support** (A, B, C families with thousands of sub-protocols each)
- **Intelligent matching** of input JSON with protocol templates
- **Variable extraction** from input data (regular and special variables)
- **Template rendering** using Jinja2 engine with enhanced context support
- **Special variable handling** with unified ConversionContext-based functions
- **Database storage** using SQLAlchemy
- **Command-line interface** for integration and usage

## System Architecture

```
protocol_converter/
├── core/                      # Core conversion logic (modular)
│   ├── converter.py           # Main converter class (simplified)
│   ├── matcher.py             # Protocol matching logic
│   ├── extractor.py           # Variable extraction engine
│   └── renderer.py            # Template rendering engine
├── models/                    # Data models
│   ├── types.py               # Core data classes (ArrayMarker, ConversionContext, etc.)
│   └── models.py              # SQLAlchemy model definitions
├── converters/                # Conversion functions
│   └── functions.py           # Unified context-based converter functions
├── database/                  # Database operations
│   ├── connection.py          # Database connection
│   └── manager.py             # Database management
├── protocols/                 # Protocol loading
│   └── loader.py              # Protocol file loader
├── protocol_manager/          # Protocol management
│   └── manager.py             # Protocol manager
├── utils/                     # Utility functions
│   └── json_utils.py          # JSON processing utilities
├── cli/                       # Command-line interface
│   └── main.py                # CLI main program
└── tests/                     # Test files
    ├── test_system.py         # Basic system tests
    ├── test_unified_context.py # ConversionContext tests
    └── test_array_context.py   # Dynamic array tests
```

## Core Components

### 1. Data Models (models/types.py)
- **ConversionContext**: Rich context object containing protocol info, array metadata, progress tracking, and debug information
- **ArrayMarker**: Handles dynamic array processing markers
- **ProtocolTemplate**: Protocol template definitions
- **ConversionResult**: Conversion result encapsulation

### 2. Core Modules
- **ProtocolMatcher** (core/matcher.py): Intelligent protocol matching with nested structure support
- **VariableExtractor** (core/extractor.py): Variable extraction engine with dynamic array support
- **TemplateRenderer** (core/renderer.py): Jinja2 template rendering with context awareness
- **ProtocolConverter** (core/converter.py): Main orchestrator coordinating all modules

### 3. Converter Functions (converters/functions.py)
- **Unified Signature**: All functions use `func(context: ConversionContext) -> str` signature
- **Rich Context Access**: Functions can access array indices, progress info, protocol metadata, etc.
- **Enhanced Functions**:
  - `func_session_id`, `func_session_id_v2`: Context-aware session ID generation
  - `func_array_index`, `func_array_total`: Array information access
  - `func_progress`, `func_is_last_item`: Progress tracking
  - `func_conversion_id`, `func_current_path`: Metadata access

### 4. Protocol Manager & Database
- **ProtocolManager** (protocol_manager/manager.py): Protocol lifecycle management
- **Database Models** (models/models.py): SQLAlchemy models for persistence

## Variable Types

### Regular Variables
- Format: `{{ variable_name }}`
- Examples: `{{ phone_type }}`, `{{ person }}`
- Processing: Directly extracted from input data based on template field mapping

### Special Variables
- Format: `{{ __variable_name }}`
- Examples: `{{ __session_id }}`, `{{ __array_index }}`, `{{ __progress }}`
- Processing: Called through unified converter functions with rich context

### Dynamic Array Support
- Array Marker: `"{# array_dynamic: true #}"`
- Context Variables: Each array element gets index, total, and progress information
- Session IDs: Different for each array element based on context

## Common Development Commands

### Installation and Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Or using make
make install

# Initialize database
python cli.py init-db
make init-db

# Load protocol files
python cli.py load -d ./examples/protocols
make load
```

### Running Tests

```bash
# Run basic system tests
python test_system.py

# Run unified context tests (new ConversionContext features)
python test_unified_context.py

# Run dynamic array tests
python test_array_context.py

# Run all tests
make test
```

### Using the CLI

```bash
# Convert protocols
python cli.py convert -s A -t C -i ./examples/input/A-1-input.json -o output.json

# List protocol families
python cli.py list-families

# List protocols in a family
python cli.py list-protocols -f A

# Show protocol details
python cli.py show A-1
```

## Usage Examples

### Basic Conversion
```python
from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS

converter = ProtocolConverter(CONVERTER_FUNCTIONS)
result = converter.convert("A", "C", input_data)
```

### Dynamic Array with Context
```python
# Input with array
data = {
    "operation": "process",
    "items": [
        {"name": "alice", "type": "primary"},
        {"name": "bob", "type": "secondary"}
    ]
}

# Template with dynamic array
template = {
    "items": [
        "{# array_dynamic: true #}",
        {
            "name": "{{ name | capitalize }}",
            "type": "{{ type }}",
            "index": "{{ __array_index }}",
            "session_id": "{{ __session_id }}"
        }
    ]
}

# Each element gets different index and session_id
```

## Extension Points

### 1. New Converter Functions
```python
def func_custom(context: ConversionContext) -> str:
    # Access rich context information
    if context.is_array_context():
        return f"custom_item_{context.array_index}"
    return "custom_value"

# Register in CONVERTER_FUNCTIONS dictionary
```

### 2. New Protocol Families
- Create protocol files in standard format
- Use dynamic array markers for list processing
- Leverage special variables for enhanced functionality

### 3. Custom Matching Logic
- Extend ProtocolMatcher class
- Implement specialized matching algorithms
- Add protocol validation logic

### 4. Enhanced Context Processing
- Access array metadata: `context.array_index`, `context.array_total`
- Track progress: `context.get_progress_info()`
- Debug information: `context.add_debug_info()`

## Advanced Features

### ConversionContext Rich Information
- **Protocol Info**: `source_protocol_id`, `target_protocol_id`, `protocol_family`
- **Array Info**: `array_path`, `array_index`, `array_total`, `current_element`
- **Progress Tracking**: `processed_items`, `is_last_item`, progress percentage
- **Path Tracking**: `current_path`, `parent_path`, `render_depth`
- **Metadata**: `timestamp`, `conversion_id`, `debug_info`

### Dynamic Array Processing
- Automatic detection of array structures
- Context-aware rendering for each element
- Progress tracking and indexing
- Custom session IDs per element

### Backward Compatibility
- All existing functionality preserved
- Old protocol templates continue to work
- Gradual migration path to enhanced features