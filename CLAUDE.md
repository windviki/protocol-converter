# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Rules

- 永远用中文回复我
- 每次重要修改需要在本地提交git
- python版本3.11
- 尊重工程的文件夹结构规范，不要随意放置文件

## Project Overview

This is a universal protocol conversion system based on Jinja2 templates that supports flexible conversion between multiple protocol families (A, B, C). The system automatically matches input JSON with protocol templates and finds the most suitable conversion path.

## Key Features

- Multi-protocol family support (A, B, C families with thousands of sub-protocols each)
- Intelligent matching of input JSON with protocol templates
- Variable extraction from input data (regular and special variables)
- Template rendering using Jinja2 engine
- Special variable handling with custom functions
- Database storage using SQLAlchemy
- Command-line interface for integration and usage

## System Architecture

```
protocol_converter/
├── core/              # Core conversion logic
│   └── converter.py   # Main converter class
├── models/            # Data models
│   └── models.py      # SQLAlchemy model definitions
├── database/          # Database operations
│   ├── connection.py  # Database connection
│   └── manager.py     # Database management
├── protocols/         # Protocol loading
│   └── loader.py      # Protocol file loader
├── converters/        # Conversion functions
│   └── functions.py   # Special variable processing functions
├── utils/             # Utility functions
│   └── json_utils.py  # JSON processing utilities
├── protocol_manager/  # Protocol management
│   └── manager.py     # Protocol manager
└── cli/               # Command-line interface
   └── main.py        # CLI main program
```

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
# Run tests
python test_system.py
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

## Core Components

1. **ProtocolConverter** (core/converter.py): Main conversion engine with protocol matching, variable extraction, and template rendering
2. **ProtocolManager** (protocol_manager/manager.py): Handles protocol loading, storage, and retrieval
3. **Converter Functions** (converters/functions.py): Special variable processing functions (func_sid, func_label, etc.)
4. **Database Models** (models/models.py): SQLAlchemy models for ProtocolFamily, Protocol, and ConversionLog
5. **CLI Interface** (cli/main.py): Command-line interface for all operations

## Variable Types

1. **Regular Variables**: `{{ variable_name }}` - Directly extracted from input data
2. **Special Variables**: `{{ __variable_name }}` - Processed by custom functions like `func_sid()`, `func_label()`, etc.

## Extension Points

1. **New Protocol Families**: Create new protocol files in the standard format
2. **New Converter Functions**: Add functions to converters/functions.py and register them
3. **New Matching Algorithms**: Extend the ProtocolMatcher class
4. **New Storage Backends**: Replace the database connection and manager