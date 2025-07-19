#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV导入器模块
用于从CSV文件导入配方数据到SQLite数据库
"""

import csv
import os
from typing import List, Dict, Any, Optional, Tuple
from .database import DatabaseManager


class CSVImporter:
    """CSV导入器类"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def import_base_materials_from_csv(self, csv_file_path: str) -> Tuple[bool, str, int]:
        """
        从CSV文件导入原材料
        CSV格式: name,description
        :param csv_file_path: CSV文件路径
        :return: (成功标志, 消息, 导入数量)
        """
        try:
            if not os.path.exists(csv_file_path):
                return False, f"文件不存在: {csv_file_path}", 0
            
            imported_count = 0
            
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                
                # 检查必需的列
                if 'name' not in reader.fieldnames:
                    return False, "CSV文件缺少必需的'name'列", 0
                
                for row in reader:
                    name = row.get('name', '').strip()
                    description = row.get('description', '').strip()
                    
                    if not name:
                        continue
                    
                    try:
                        # 检查是否已存在
                        existing = self.db_manager.get_base_material_by_name(name)
                        if not existing:
                            self.db_manager.add_base_material(name, description or None)
                            imported_count += 1
                    except Exception as e:
                        print(f"导入原材料 {name} 时出错: {e}")
                        continue
            
            return True, f"成功导入 {imported_count} 个原材料", imported_count
            
        except Exception as e:
            return False, f"导入失败: {str(e)}", 0
    
    def import_materials_from_csv(self, csv_file_path: str) -> Tuple[bool, str, int]:
        """
        从CSV文件导入半成品
        CSV格式: name,output_quantity,description,ingredient_type_1,ingredient_name_1,quantity_1,...
        :param csv_file_path: CSV文件路径
        :return: (成功标志, 消息, 导入数量)
        """
        try:
            if not os.path.exists(csv_file_path):
                return False, f"文件不存在: {csv_file_path}", 0
            
            imported_count = 0
            
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                
                # 检查必需的列
                required_cols = ['name']
                for col in required_cols:
                    if col not in reader.fieldnames:
                        return False, f"CSV文件缺少必需的'{col}'列", 0
                
                for row in reader:
                    name = row.get('name', '').strip()
                    output_quantity = int(row.get('output_quantity', 1))
                    description = row.get('description', '').strip()
                    
                    if not name:
                        continue
                    
                    try:
                        # 检查是否已存在
                        existing = self.db_manager.get_material_by_name(name)
                        if existing:
                            continue
                        
                        # 添加半成品
                        material_id = self.db_manager.add_material(name, output_quantity, description or None)
                        
                        # 处理配方需求
                        self._process_recipe_requirements(row, 'material', material_id)
                        
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"导入半成品 {name} 时出错: {e}")
                        continue
            
            return True, f"成功导入 {imported_count} 个半成品", imported_count
            
        except Exception as e:
            return False, f"导入失败: {str(e)}", 0
    
    def import_products_from_csv(self, csv_file_path: str) -> Tuple[bool, str, int]:
        """
        从CSV文件导入成品
        CSV格式: name,output_quantity,description,ingredient_type_1,ingredient_name_1,quantity_1,...
        :param csv_file_path: CSV文件路径
        :return: (成功标志, 消息, 导入数量)
        """
        try:
            if not os.path.exists(csv_file_path):
                return False, f"文件不存在: {csv_file_path}", 0
            
            imported_count = 0
            
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                
                # 检查必需的列
                required_cols = ['name']
                for col in required_cols:
                    if col not in reader.fieldnames:
                        return False, f"CSV文件缺少必需的'{col}'列", 0
                
                for row in reader:
                    name = row.get('name', '').strip()
                    output_quantity = int(row.get('output_quantity', 1))
                    description = row.get('description', '').strip()
                    
                    if not name:
                        continue
                    
                    try:
                        # 检查是否已存在
                        existing = self.db_manager.get_product_by_name(name)
                        if existing:
                            continue
                        
                        # 添加成品
                        product_id = self.db_manager.add_product(name, output_quantity, description or None)
                        
                        # 处理配方需求
                        self._process_recipe_requirements(row, 'product', product_id)
                        
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"导入成品 {name} 时出错: {e}")
                        continue
            
            return True, f"成功导入 {imported_count} 个成品", imported_count
            
        except Exception as e:
            return False, f"导入失败: {str(e)}", 0
    
    def _process_recipe_requirements(self, row: Dict[str, str], recipe_type: str, recipe_id: int):
        """处理配方需求"""
        # 查找所有成分列
        ingredient_index = 1
        while True:
            type_col = f'ingredient_type_{ingredient_index}'
            name_col = f'ingredient_name_{ingredient_index}'
            qty_col = f'quantity_{ingredient_index}'
            
            if type_col not in row or name_col not in row or qty_col not in row:
                break
            
            ingredient_type = row[type_col].strip()
            ingredient_name = row[name_col].strip()
            quantity_str = row[qty_col].strip()
            
            if not ingredient_type or not ingredient_name or not quantity_str:
                ingredient_index += 1
                continue
            
            try:
                quantity = float(quantity_str)
                
                # 根据类型查找成分ID
                ingredient_id = None
                if ingredient_type == 'base':
                    item = self.db_manager.get_base_material_by_name(ingredient_name)
                    if item:
                        ingredient_id = item['id']
                elif ingredient_type == 'material':
                    item = self.db_manager.get_material_by_name(ingredient_name)
                    if item:
                        ingredient_id = item['id']
                
                if ingredient_id:
                    self.db_manager.add_recipe_requirement(
                        recipe_type, recipe_id, ingredient_type, ingredient_id, quantity
                    )
                
            except ValueError:
                print(f"无效的数量值: {quantity_str}")
            
            ingredient_index += 1
    
    def export_base_materials_to_csv(self, csv_file_path: str) -> Tuple[bool, str]:
        """导出原材料到CSV文件"""
        try:
            materials = self.db_manager.get_base_materials()
            
            with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(['name', 'description'])
                
                for material in materials:
                    writer.writerow([
                        material['name'],
                        material.get('description', '')
                    ])
            
            return True, f"成功导出 {len(materials)} 个原材料到 {csv_file_path}"
            
        except Exception as e:
            return False, f"导出失败: {str(e)}"
    
    def export_materials_to_csv(self, csv_file_path: str) -> Tuple[bool, str]:
        """导出半成品到CSV文件"""
        try:
            materials = self.db_manager.get_materials()
            
            with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                
                # 写入表头
                headers = ['name', 'output_quantity', 'description']
                # 添加最多10个成分列
                for i in range(1, 11):
                    headers.extend([f'ingredient_type_{i}', f'ingredient_name_{i}', f'quantity_{i}'])
                writer.writerow(headers)
                
                for material in materials:
                    row = [
                        material['name'],
                        material.get('output_quantity', 1),
                        material.get('description', '')
                    ]
                    
                    # 获取配方需求
                    requirements = self.db_manager.get_recipe_requirements('material', material['id'])
                    
                    # 添加成分信息
                    for i, req in enumerate(requirements[:10]):
                        ingredient_name = self._get_ingredient_name(req['ingredient_type'], req['ingredient_id'])
                        row.extend([req['ingredient_type'], ingredient_name, req['quantity']])
                    
                    # 填充空列
                    while len(row) < len(headers):
                        row.append('')
                    
                    writer.writerow(row)
            
            return True, f"成功导出 {len(materials)} 个半成品到 {csv_file_path}"
            
        except Exception as e:
            return False, f"导出失败: {str(e)}"
    
    def export_products_to_csv(self, csv_file_path: str) -> Tuple[bool, str]:
        """导出成品到CSV文件"""
        try:
            products = self.db_manager.get_products()
            
            with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                
                # 写入表头
                headers = ['name', 'output_quantity', 'description']
                # 添加最多10个成分列
                for i in range(1, 11):
                    headers.extend([f'ingredient_type_{i}', f'ingredient_name_{i}', f'quantity_{i}'])
                writer.writerow(headers)
                
                for product in products:
                    row = [
                        product['name'],
                        product.get('output_quantity', 1),
                        product.get('description', '')
                    ]
                    
                    # 获取配方需求
                    requirements = self.db_manager.get_recipe_requirements('product', product['id'])
                    
                    # 添加成分信息
                    for i, req in enumerate(requirements[:10]):
                        ingredient_name = self._get_ingredient_name(req['ingredient_type'], req['ingredient_id'])
                        row.extend([req['ingredient_type'], ingredient_name, req['quantity']])
                    
                    # 填充空列
                    while len(row) < len(headers):
                        row.append('')
                    
                    writer.writerow(row)
            
            return True, f"成功导出 {len(products)} 个成品到 {csv_file_path}"
            
        except Exception as e:
            return False, f"导出失败: {str(e)}"
    
    def _get_ingredient_name(self, ingredient_type: str, ingredient_id: int) -> str:
        """获取成分名称"""
        if ingredient_type == 'base':
            item = self.db_manager.get_base_material_by_id(ingredient_id)
        elif ingredient_type == 'material':
            item = self.db_manager.get_material_by_id(ingredient_id)
        else:
            return ''
        
        return item['name'] if item else f'未知({ingredient_id})'
    
    def create_csv_templates(self, output_dir: str) -> Tuple[bool, str]:
        """创建CSV模板文件"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 原材料模板
            base_template_path = os.path.join(output_dir, 'base_materials_template.csv')
            with open(base_template_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(['name', 'description'])
                writer.writerow(['示例原材料', '这是一个示例描述'])
            
            # 半成品模板
            material_template_path = os.path.join(output_dir, 'materials_template.csv')
            with open(material_template_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                headers = ['name', 'output_quantity', 'description']
                for i in range(1, 4):  # 示例3个成分
                    headers.extend([f'ingredient_type_{i}', f'ingredient_name_{i}', f'quantity_{i}'])
                writer.writerow(headers)
                writer.writerow([
                    '示例半成品', 1, '这是一个示例半成品',
                    'base', '示例原材料1', 2,
                    'base', '示例原材料2', 1,
                    'material', '示例半成品依赖', 1
                ])
            
            # 成品模板
            product_template_path = os.path.join(output_dir, 'products_template.csv')
            with open(product_template_path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                headers = ['name', 'output_quantity', 'description']
                for i in range(1, 4):  # 示例3个成分
                    headers.extend([f'ingredient_type_{i}', f'ingredient_name_{i}', f'quantity_{i}'])
                writer.writerow(headers)
                writer.writerow([
                    '示例成品', 1, '这是一个示例成品',
                    'base', '示例原材料1', 3,
                    'material', '示例半成品', 2,
                    '', '', ''
                ])
            
            return True, f"CSV模板已创建在: {output_dir}"
            
        except Exception as e:
            return False, f"创建模板失败: {str(e)}"
    
    def export_template(self, file_path: str) -> bool:
        """导出简化格式的CSV模板文件"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(['物品名称', '物品类型', '所需材料'])
                # 写入示例数据
                writer.writerow(['示例半成品', '半成品', '示例原材料1(2) 示例原材料2'])
                writer.writerow(['示例成品', '成品', '示例半成品 示例原材料1(3)'])
            return True
        except Exception as e:
            print(f"导出模板失败: {str(e)}")
            return False