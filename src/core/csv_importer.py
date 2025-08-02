#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV导入器模块
用于从CSV文件导入配方数据到SQLite数据库
"""

import csv
import os
import re
from typing import List, Dict, Any, Tuple
from .database import DatabaseManager

class CSVImporter:
    """适配实际CSV格式的导入器，只支持中文列头"""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager  # 由外部传入，已保证用根目录

    def import_from_csv(self, csv_file_path: str) -> Dict[str, Any]:
        """
        从CSV文件导入配方数据，支持中文列头：物品名称,物品类型,所需材料
        :param csv_file_path: CSV文件路径
        :return: 导入结果统计
        """
        result = {
            'success': True,
            'message': '',
            'imported_counts': {
                'base_materials': 0,
                'materials': 0,
                'products': 0
            },
            'errors': []
        }
        if not os.path.exists(csv_file_path):
            result['success'] = False
            result['message'] = f"文件不存在: {csv_file_path}"
            return result
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                # 检查列头
                required_cols = ['物品名称', '物品类型', '所需材料']
                if not all(col in reader.fieldnames for col in required_cols):
                    result['success'] = False
                    result['message'] = f"CSV文件缺少必需列: {required_cols}"
                    return result
                for idx, row in enumerate(reader):
                    name = row['物品名称'].strip()
                    item_type = row['物品类型'].strip()
                    requirements_str = row['所需材料'].strip()
                    if not name or not item_type:
                        continue
                    try:
                        if item_type == '半成品':
                            # 检查是否已存在
                            existing = self.db_manager.get_material_by_name(name)
                            if existing:
                                continue
                            material_id = self.db_manager.add_material(name, 1, None)
                            reqs = self._parse_requirements(requirements_str)
                            for req_name, qty in reqs:
                                # 检查是否有半成品标记[m]
                                if req_name.startswith('[m]'):
                                    # 去掉[m]标记，作为半成品处理
                                    actual_name = req_name[3:]
                                    mat = self.db_manager.get_material_by_name(actual_name)
                                    if mat:
                                        self.db_manager.add_recipe_requirement('material', material_id, 'material', mat['id'], qty)
                                    else:
                                        # 如果半成品不存在，跳过或报错
                                        result['errors'].append(f"第{idx+2}行: 半成品'{actual_name}'不存在")
                                else:
                                    # 只允许原材料作为半成品成分
                                    base = self.db_manager.get_base_material_by_name(req_name)
                                    if not base:
                                        # 自动添加原材料
                                        base_id = self.db_manager.add_base_material(req_name, None)
                                        base = self.db_manager.get_base_material_by_name(req_name)
                                    self.db_manager.add_recipe_requirement('material', material_id, 'base', base['id'], qty)
                            result['imported_counts']['materials'] += 1
                        elif item_type == '成品':
                            existing = self.db_manager.get_product_by_name(name)
                            if existing:
                                continue
                            product_id = self.db_manager.add_product(name, 1, None)
                            reqs = self._parse_requirements(requirements_str)
                            for req_name, qty in reqs:
                                # 检查是否有半成品标记[m]
                                if req_name.startswith('[m]'):
                                    # 去掉[m]标记，作为半成品处理
                                    actual_name = req_name[3:]
                                    mat = self.db_manager.get_material_by_name(actual_name)
                                    if mat:
                                        self.db_manager.add_recipe_requirement('product', product_id, 'material', mat['id'], qty)
                                    else:
                                        # 如果半成品不存在，跳过或报错
                                        result['errors'].append(f"第{idx+2}行: 半成品'{actual_name}'不存在")
                                else:
                                    # 先查半成品，再查原材料
                                    mat = self.db_manager.get_material_by_name(req_name)
                                    if mat:
                                        self.db_manager.add_recipe_requirement('product', product_id, 'material', mat['id'], qty)
                                    else:
                                        base = self.db_manager.get_base_material_by_name(req_name)
                                        if not base:
                                            base_id = self.db_manager.add_base_material(req_name, None)
                                            base = self.db_manager.get_base_material_by_name(req_name)
                                        self.db_manager.add_recipe_requirement('product', product_id, 'base', base['id'], qty)
                            result['imported_counts']['products'] += 1
                        else:
                            # 其它类型视为原材料
                            if not self.db_manager.get_base_material_by_name(name):
                                self.db_manager.add_base_material(name, None)
                                result['imported_counts']['base_materials'] += 1
                    except Exception as e:
                        result['errors'].append(f"第{idx+2}行导入失败: {str(e)}")
            if result['errors']:
                result['success'] = False
                result['message'] = f"导入完成，但有 {len(result['errors'])} 个错误"
            else:
                result['message'] = "导入成功"
        except Exception as e:
            result['success'] = False
            result['message'] = f"导入失败: {str(e)}"
            result['errors'].append(str(e))
        return result

    def _parse_requirements(self, requirements_str: str) -> List[Tuple[str, float]]:
        """
        解析所需材料字符串，返回[(材料名, 数量)]
        如："亚麻(2) 明矾" -> [("亚麻",2), ("明矾",1)]
        """
        result = []
        if not requirements_str:
            return result
        # 匹配“材料名(数量)”或“材料名”
        pattern = re.compile(r'([^\s()]+)(?:\((\d+)\))?')
        for match in pattern.finditer(requirements_str):
            name = match.group(1).strip()
            qty = int(match.group(2)) if match.group(2) else 1
            result.append((name, qty))
        return result