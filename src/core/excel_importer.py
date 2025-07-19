import pandas as pd
from typing import Dict, List, Any, Optional
from .database import DatabaseManager
import logging


class ExcelImporter:
    """Excel配方数据导入器"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        if db_manager is None:
            self.db_manager = DatabaseManager()
        else:
            self.db_manager = db_manager
        
        self.logger = logging.getLogger(__name__)
    
    def import_from_excel(self, file_path: str, sheet_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        """
        从Excel文件导入配方数据
        :param file_path: Excel文件路径
        :param sheet_mapping: 工作表映射，格式: {'base': '原材料', 'materials': '半成品', 'products': '成品'}
        :return: 导入结果统计
        """
        if sheet_mapping is None:
            sheet_mapping = {
                'base': '原材料',
                'materials': '半成品', 
                'products': '成品'
            }
        
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
        
        try:
            # 读取Excel文件
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            # 导入原材料
            if sheet_mapping['base'] in excel_data:
                base_count = self._import_base_materials(excel_data[sheet_mapping['base']], result['errors'])
                result['imported_counts']['base_materials'] = base_count
            
            # 导入半成品
            if sheet_mapping['materials'] in excel_data:
                materials_count = self._import_materials(excel_data[sheet_mapping['materials']], result['errors'])
                result['imported_counts']['materials'] = materials_count
            
            # 导入成品
            if sheet_mapping['products'] in excel_data:
                products_count = self._import_products(excel_data[sheet_mapping['products']], result['errors'])
                result['imported_counts']['products'] = products_count
            
            if result['errors']:
                result['success'] = False
                result['message'] = f"导入完成，但有 {len(result['errors'])} 个错误"
            else:
                result['message'] = "导入成功"
                
        except Exception as e:
            result['success'] = False
            result['message'] = f"导入失败: {str(e)}"
            result['errors'].append(str(e))
            self.logger.error(f"Excel导入失败: {e}")
        
        return result
    
    def _import_base_materials(self, df: pd.DataFrame, errors: List[str]) -> int:
        """导入原材料数据"""
        count = 0
        required_columns = ['名称']
        
        # 检查必需列
        if not all(col in df.columns for col in required_columns):
            errors.append(f"原材料工作表缺少必需列: {required_columns}")
            return 0
        
        for index, row in df.iterrows():
            try:
                name = str(row['名称']).strip()
                if not name or name == 'nan':
                    continue
                
                # 检查是否已存在
                existing = self.db_manager.get_base_material_by_name(name)
                if existing:
                    continue
                
                # 添加原材料
                self.db_manager.add_base_material(name)
                count += 1
                
            except Exception as e:
                errors.append(f"原材料第{index+2}行导入失败: {str(e)}")
        
        return count
    
    def _import_materials(self, df: pd.DataFrame, errors: List[str]) -> int:
        """导入半成品数据"""
        count = 0
        required_columns = ['名称', '产出数量']
        
        # 检查必需列
        if not all(col in df.columns for col in required_columns):
            errors.append(f"半成品工作表缺少必需列: {required_columns}")
            return 0
        
        for index, row in df.iterrows():
            try:
                name = str(row['名称']).strip()
                if not name or name == 'nan':
                    continue
                
                output_quantity = int(row['产出数量']) if pd.notna(row['产出数量']) else 1
                
                # 检查是否已存在
                existing = self.db_manager.get_material_by_name(name)
                if existing:
                    continue
                
                # 添加半成品
                material_id = self.db_manager.add_material(name, output_quantity)
                
                # 处理配方需求
                self._process_recipe_requirements(row, 'material', material_id, errors, index)
                
                count += 1
                
            except Exception as e:
                errors.append(f"半成品第{index+2}行导入失败: {str(e)}")
        
        return count
    
    def _import_products(self, df: pd.DataFrame, errors: List[str]) -> int:
        """导入成品数据"""
        count = 0
        required_columns = ['名称', '产出数量']
        
        # 检查必需列
        if not all(col in df.columns for col in required_columns):
            errors.append(f"成品工作表缺少必需列: {required_columns}")
            return 0
        
        for index, row in df.iterrows():
            try:
                name = str(row['名称']).strip()
                if not name or name == 'nan':
                    continue
                
                output_quantity = int(row['产出数量']) if pd.notna(row['产出数量']) else 1
                
                # 检查是否已存在
                existing = self.db_manager.get_product_by_name(name)
                if existing:
                    continue
                
                # 添加成品
                product_id = self.db_manager.add_product(name, output_quantity)
                
                # 处理配方需求
                self._process_recipe_requirements(row, 'product', product_id, errors, index)
                
                count += 1
                
            except Exception as e:
                errors.append(f"成品第{index+2}行导入失败: {str(e)}")
        
        return count
    
    def _process_recipe_requirements(self, row: pd.Series, item_type: str, item_id: int, 
                                   errors: List[str], row_index: int):
        """处理配方需求"""
        # 查找所有材料列（格式：原材料_名称, 原材料_数量, 半成品_名称, 半成品_数量等）
        ingredient_types = ['原材料', '半成品']
        
        for ing_type in ingredient_types:
            name_col = f'{ing_type}_名称'
            qty_col = f'{ing_type}_数量'
            
            # 支持多个同类型材料（如：原材料1_名称, 原材料1_数量, 原材料2_名称, 原材料2_数量）
            i = 1
            while True:
                if i == 1:
                    current_name_col = name_col
                    current_qty_col = qty_col
                else:
                    current_name_col = f'{ing_type}{i}_名称'
                    current_qty_col = f'{ing_type}{i}_数量'
                
                if current_name_col not in row.index:
                    break
                
                ingredient_name = str(row[current_name_col]).strip() if pd.notna(row[current_name_col]) else ''
                if not ingredient_name or ingredient_name == 'nan':
                    i += 1
                    continue
                
                try:
                    quantity = float(row[current_qty_col]) if pd.notna(row[current_qty_col]) else 1
                except (ValueError, KeyError):
                    quantity = 1
                
                # 查找材料ID
                ingredient_id = None
                ingredient_db_type = None
                
                if ing_type == '原材料':
                    base_material = self.db_manager.get_base_material_by_name(ingredient_name)
                    if base_material:
                        ingredient_id = base_material['id']
                        ingredient_db_type = 'base'
                elif ing_type == '半成品':
                    material = self.db_manager.get_material_by_name(ingredient_name)
                    if material:
                        ingredient_id = material['id']
                        ingredient_db_type = 'material'
                
                if ingredient_id is None:
                    errors.append(f"第{row_index+2}行: 找不到{ing_type} '{ingredient_name}'")
                else:
                    # 添加配方需求
                    self.db_manager.add_recipe_requirement(
                        item_type, item_id, ingredient_db_type, ingredient_id, quantity
                    )
                
                i += 1
    
    def export_template(self, file_path: str) -> bool:
        """导出Excel模板文件"""
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 原材料模板
                base_template = pd.DataFrame({
                    '名称': ['示例原材料1', '示例原材料2']
                })
                base_template.to_excel(writer, sheet_name='原材料', index=False)
                
                # 半成品模板
                materials_template = pd.DataFrame({
                    '名称': ['示例半成品1', '示例半成品2'],
                    '产出数量': [1, 2],
                    '原材料_名称': ['示例原材料1', '示例原材料1'],
                    '原材料_数量': [3, 5],
                    '原材料2_名称': ['示例原材料2', ''],
                    '原材料2_数量': [1, 0]
                })
                materials_template.to_excel(writer, sheet_name='半成品', index=False)
                
                # 成品模板
                products_template = pd.DataFrame({
                    '名称': ['示例成品1', '示例成品2'],
                    '产出数量': [1, 1],
                    '原材料_名称': ['示例原材料1', ''],
                    '原材料_数量': [2, 0],
                    '半成品_名称': ['示例半成品1', '示例半成品2'],
                    '半成品_数量': [1, 3]
                })
                products_template.to_excel(writer, sheet_name='成品', index=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出模板失败: {e}")
            return False
    
    def validate_excel_format(self, file_path: str, sheet_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        """验证Excel文件格式"""
        if sheet_mapping is None:
            sheet_mapping = {
                'base': '原材料',
                'materials': '半成品',
                'products': '成品'
            }
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            # 检查工作表是否存在
            for sheet_type, sheet_name in sheet_mapping.items():
                if sheet_name not in excel_data:
                    result['warnings'].append(f"缺少工作表: {sheet_name}")
                    continue
                
                df = excel_data[sheet_name]
                
                # 检查必需列
                if sheet_type == 'base':
                    required_cols = ['名称']
                else:
                    required_cols = ['名称', '产出数量']
                
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    result['errors'].append(f"工作表 '{sheet_name}' 缺少必需列: {missing_cols}")
                    result['valid'] = False
        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"读取Excel文件失败: {str(e)}")
        
        return result