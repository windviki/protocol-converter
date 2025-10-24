#!/usr/bin/env python3
"""
协议转换器Web界面
"""

import sys
import os
import json
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_database
from protocol_manager.manager import ProtocolManager
from core.converter import ProtocolConverter
from converters.functions import CONVERTER_FUNCTIONS

app = Flask(__name__)
app.secret_key = 'protocol-converter-secret-key'

# 全局变量
manager = None
converter = None


def init_app():
    """初始化应用"""
    global manager, converter
    
    try:
        # 初始化数据库
        init_database()
        
        # 创建管理器和转换器
        manager = ProtocolManager()
        converter = ProtocolConverter(CONVERTER_FUNCTIONS)
        
        # 加载协议
        examples_dir = os.path.join(os.path.dirname(__file__), "examples", "protocols")
        if os.path.exists(examples_dir):
            result = manager.load_protocols_from_directory(examples_dir)
            
            # 加载协议到转换器
            families = manager.list_all_families()
            for family in families:
                protocols = manager.get_protocols_by_family(family)
                for protocol_id in protocols:
                    protocol_info = manager.get_protocol_by_id(protocol_id)
                    if protocol_info:
                        converter.load_protocol(
                            protocol_id=protocol_id,
                            protocol_family=protocol_info['family'],
                            template_content=protocol_info['template']
                        )
        
        print("应用初始化完成")
        
    except Exception as e:
        print(f"应用初始化失败: {e}")


@app.route('/')
def index():
    """首页"""
    try:
        families = manager.list_all_families()
        protocols_info = {}
        
        for family in families:
            protocols = manager.get_protocols_by_family(family)
            protocols_info[family] = protocols
        
        return render_template('index.html', 
                             families=families, 
                             protocols_info=protocols_info)
    except Exception as e:
        return f"错误: {e}", 500


@app.route('/convert', methods=['POST'])
def convert():
    """转换协议"""
    try:
        data = request.get_json()
        
        source_protocol = data.get('source_protocol')
        target_protocol = data.get('target_protocol')
        input_json = data.get('input_json')
        
        if not all([source_protocol, target_protocol, input_json]):
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        # 解析输入JSON
        try:
            source_data = json.loads(input_json)
        except json.JSONDecodeError:
            return jsonify({'success': False, 'error': '输入JSON格式错误'})
        
        # 执行转换
        result = converter.convert(source_protocol, target_protocol, source_data)
        
        if result.success:
            return jsonify({
                'success': True,
                'result': result.result,
                'matched_protocol': result.matched_protocol,
                'variables': result.variables
            })
        else:
            return jsonify({'success': False, 'error': result.error})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/protocols/<protocol_id>')
def protocol_detail(protocol_id):
    """协议详情"""
    try:
        protocol_info = manager.get_protocol_by_id(protocol_id)
        if protocol_info:
            return render_template('protocol_detail.html', 
                                 protocol_id=protocol_id,
                                 protocol_info=protocol_info)
        else:
            return f"协议 {protocol_id} 不存在", 404
    except Exception as e:
        return f"错误: {e}", 500


@app.route('/api/families')
def api_families():
    """获取协议族列表API"""
    try:
        families = manager.list_all_families()
        return jsonify({'success': True, 'families': families})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/protocols/<family>')
def api_protocols(family):
    """获取指定协议族的协议列表API"""
    try:
        protocols = manager.get_protocols_by_family(family)
        return jsonify({'success': True, 'protocols': protocols})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/protocol/<protocol_id>')
def api_protocol(protocol_id):
    """获取协议详情API"""
    try:
        protocol_info = manager.get_protocol_by_id(protocol_id)
        if protocol_info:
            return jsonify({'success': True, 'protocol': protocol_info})
        else:
            return jsonify({'success': False, 'error': '协议不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    # 初始化应用
    init_app()
    
    # 创建模板目录
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # 启动Web服务器
    print("启动Web服务器...")
    print("请访问: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)