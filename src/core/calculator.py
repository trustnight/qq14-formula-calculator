from collections import defaultdict
from typing import Dict, List, Any, Optional
from .database import DatabaseManager


class BOMCalculator:
    """BOM计算器，基于SQLite数据库进行配方计算"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        if db_manager is None:
            self.db_manager = DatabaseManager()
        else:
            self.db_manager = db_manager
    
    def calculate_requirements_by_name(self, item_type: str, item_name: str, quantity: float = 1) -> Dict[int, float]:
        """
        根据物品名称计算制作指定数量物品所需的所有基础材料
        :param item_type: 'product' 或 'material'
        :param item_name: 物品名称
        :param quantity: 需要制作的数量
        :return: 基础材料需求字典 {base_id: required_quantity}
        """
        # 根据名称查找物品
        if item_type == 'product':
            item = self.db_manager.get_product_by_name(item_name)
        elif item_type == 'material':
            item = self.db_manager.get_material_by_name(item_name)
        else:
            raise ValueError(f"不支持的物品类型: {item_type}")
        
        if not item:
            raise RuntimeError(f"{item_type}中'{item_name}'不存在")
        
        return self.calculate_requirements_by_id(item_type, item['id'], quantity)
    
    def calculate_requirements_by_id(self, item_type: str, item_id: int, quantity: float = 1, 
                                   include_all_levels: bool = False) -> Dict[int, float]:
        """
        根据物品ID计算制作指定数量物品所需的材料
        :param item_type: 'product' 或 'material'
        :param item_id: 物品ID
        :param quantity: 需要制作的数量
        :param include_all_levels: 是否包含所有层级的材料（默认为False，只返回基础材料）
        :return: 材料需求字典
        """
        if include_all_levels:
            # 返回完整的材料树结构
            return self._calculate_full_tree(item_type, item_id, quantity)
        else:
            # 保持原有逻辑，只返回基础材料
            requirements = defaultdict(float)
            self._calculate(item_type, item_id, quantity, requirements)
            return dict(requirements)
    
    def _calculate_full_tree(self, item_type: str, item_id: int, quantity: float) -> Dict[str, Any]:
        """递归计算完整的材料树，包括所有层级"""
        result = {
            'id': item_id,
            'type': item_type,
            'quantity': quantity,
            'children': []
        }
        
        if item_type == 'base':
            return result
        
        # 获取物品信息和配方
        if item_type == 'product':
            item_info = self.db_manager.get_product_by_id(item_id)
            if not item_info:
                return result
            output_qty = item_info.get('output_quantity', 1)
            multiplier = quantity / output_qty
        elif item_type == 'material':
            item_info = self.db_manager.get_material_by_id(item_id)
            if not item_info:
                return result
            output_qty = item_info.get('output_quantity', 1)
            multiplier = quantity / output_qty
        else:
            return result
        
        # 获取配方需求
        requirements = self.db_manager.get_recipe_requirements(item_type, item_id)
        
        # 递归计算每个成分
        for req in requirements:
            ing_type = req['ingredient_type']
            ing_id = req['ingredient_id']
            ing_qty = req['quantity'] * multiplier
            
            child = self._calculate_full_tree(ing_type, ing_id, ing_qty)
            result['children'].append(child)
        
        return result
    
    def _calculate(self, item_type: str, item_id: int, quantity: float, requirements: Dict[int, float]):
        """递归计算基础材料需求"""
        if item_type == 'base':
            requirements[item_id] += quantity
            return
        
        # 获取物品信息
        if item_type == 'product':
            item_info = self.db_manager.get_product_by_id(item_id)
            if not item_info:
                return
            output_qty = item_info.get('output_quantity', 1)
            multiplier = quantity / output_qty
        elif item_type == 'material':
            item_info = self.db_manager.get_material_by_id(item_id)
            if not item_info:
                return
            output_qty = item_info.get('output_quantity', 1)
            multiplier = quantity / output_qty
        else:
            return
        
        # 获取配方需求
        recipe_requirements = self.db_manager.get_recipe_requirements(item_type, item_id)
        
        # 递归计算每个成分
        for req in recipe_requirements:
            ing_type = req['ingredient_type']
            ing_id = req['ingredient_id']
            ing_qty = req['quantity'] * multiplier
            
            self._calculate(ing_type, ing_id, ing_qty, requirements)
    
    def calculate_multiple_items(self, items: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        计算多个物品的总需求
        :param items: 物品列表，格式: [{'type': 'product', 'id': 1, 'quantity': 3}, ...]
        :return: 基础材料总需求
        """
        total_requirements = defaultdict(float)
        
        for item in items:
            item_type = item['type']
            item_id = item['id']
            quantity = item['quantity']
            
            # 计算单个物品需求
            item_requirements = self.calculate_requirements_by_id(item_type, item_id, quantity)
            
            # 累加到总需求
            for base_id, req_qty in item_requirements.items():
                total_requirements[base_id] += req_qty
        
        return dict(total_requirements)
    
    def get_recipe_tree(self, item_type: str, item_id: int, quantity: float = 1) -> Dict[str, Any]:
        """
        获取配方树结构，用于界面显示
        :param item_type: 物品类型
        :param item_id: 物品ID
        :param quantity: 数量
        :return: 配方树结构
        """
        def build_tree_node(node_type: str, node_id: int, node_quantity: float) -> Dict[str, Any]:
            # 获取物品信息
            if node_type == 'base':
                item_info = self.db_manager.get_base_material_by_id(node_id)
                node = {
                    'id': node_id,
                    'type': node_type,
                    'name': item_info['name'] if item_info else f'未知原材料({node_id})',
                    'quantity': node_quantity,
                    'children': []
                }
                return node
            elif node_type == 'material':
                item_info = self.db_manager.get_material_by_id(node_id)
                if not item_info:
                    return None
                
                output_qty = item_info.get('output_quantity', 1)
                multiplier = node_quantity / output_qty
                
                node = {
                    'id': node_id,
                    'type': node_type,
                    'name': item_info['name'],
                    'quantity': node_quantity,
                    'output_quantity': output_qty,
                    'children': []
                }
                
                # 获取配方需求
                requirements = self.db_manager.get_recipe_requirements(node_type, node_id)
                for req in requirements:
                    child_type = req['ingredient_type']
                    child_id = req['ingredient_id']
                    child_qty = req['quantity'] * multiplier
                    
                    child_node = build_tree_node(child_type, child_id, child_qty)
                    if child_node:
                        node['children'].append(child_node)
                
                return node
            
            elif node_type == 'product':
                item_info = self.db_manager.get_product_by_id(node_id)
                if not item_info:
                    return None
                
                output_qty = item_info.get('output_quantity', 1)
                multiplier = node_quantity / output_qty
                
                node = {
                    'id': node_id,
                    'type': node_type,
                    'name': item_info['name'],
                    'quantity': node_quantity,
                    'output_quantity': output_qty,
                    'children': []
                }
                
                # 获取配方需求
                requirements = self.db_manager.get_recipe_requirements(node_type, node_id)
                for req in requirements:
                    child_type = req['ingredient_type']
                    child_id = req['ingredient_id']
                    child_qty = req['quantity'] * multiplier
                    
                    child_node = build_tree_node(child_type, child_id, child_qty)
                    if child_node:
                        node['children'].append(child_node)
                
                return node
            
            # 如果没有匹配的类型，返回None
            return None
        
        return build_tree_node(item_type, item_id, quantity)
    
    def format_requirements_for_display(self, requirements: Dict[int, float]) -> Dict[str, Any]:
        """
        格式化需求结果用于界面显示
        :param requirements: 基础材料需求字典
        :return: 包含需求列表和总成本的字典
        """
        result = []
        total_cost = 0.0
        
        for base_id, quantity in requirements.items():
            base_material = self.db_manager.get_base_material_by_id(base_id)
            if base_material:
                cost = base_material.get('cost', 0)
                item_total_cost = cost * quantity
                total_cost += item_total_cost
                
                result.append({
                    'id': base_id,
                    'name': base_material['name'],
                    'quantity': quantity,
                    'type': 'base',
                    'cost': cost,
                    'total_cost': item_total_cost
                })
        
        # 按名称排序
        result.sort(key=lambda x: x['name'])
        
        return {
            'requirements': result,
            'total_cost': total_cost
        }
    
    def get_item_info(self, item_type: str, item_id: int) -> Optional[Dict[str, Any]]:
        """
        获取物品信息
        :param item_type: 物品类型
        :param item_id: 物品ID
        :return: 物品信息
        """
        if item_type == 'base':
            return self.db_manager.get_base_material_by_id(item_id)
        elif item_type == 'material':
            return self.db_manager.get_material_by_id(item_id)
        elif item_type == 'product':
            return self.db_manager.get_product_by_id(item_id)
        else:
            return None
