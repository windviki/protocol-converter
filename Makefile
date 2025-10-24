.PHONY: help install init-db load test clean example

help:
	@echo "协议转换器 - 可用命令:"
	@echo "  install     - 安装依赖"
	@echo "  init-db     - 初始化数据库"
	@echo "  load        - 加载协议文件"
	@echo "  test        - 运行测试"
	@echo "  example     - 运行示例"
	@echo "  clean       - 清理临时文件"
	@echo "  cli-help    - 显示CLI帮助"

install:
	pip install -r requirements.txt

init-db:
	python cli.py init-db

load:
	python cli.py load -d ./examples/protocols

test:
	python test_system.py

example:
	python example_usage.py

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name "*.db" -delete
	rm -rf protocol_converter.log

cli-help:
	python cli.py --help

# 开发快捷命令
dev-setup: install init-db load
	@echo "开发环境设置完成!"

# 转换示例命令
convert-example:
	python cli.py convert -s A -t C -i ./examples/input/A-1-input.json

list-families:
	python cli.py list-families

list-protocols:
	python cli.py list-protocols -f A

show-protocol:
	python cli.py show A-1