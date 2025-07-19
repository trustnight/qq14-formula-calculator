import json
import os
from typing import Dict, List, Any
from .database import DatabaseManager


class DataMigrator:
    """数据迁移工具，将JSON数据迁移到SQLite数据库"""
    
    def __init__(self, db_manager: DatabaseManager = None, json_data_path: str = None):
        if db_manager is None:
            self.db_manager = DatabaseManager()
        else:
            self.db_manager = db_manager
            
        if json_data_path is None:
            self.json_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        else:
            self.json_data_path = json_data_path
    
    def load_json_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载所有JSON数据"""
        data = {}
        
        # 加载原材料数据
        base_path = os.path.join(self.json_data_path, 'base', 'index.json')
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                data['base'] = json.load(f)
        else:
            data['base'] = []
        
        # 加载半成品数据
        materials_path = os.path.join(self.json_data_path, 'materials', 'index.json')
        if os.path.exists(materials_path):
            with open(materials_path, 'r', encoding='utf-8') as f:
                data['materials'] = json.load(f)
        else:
            data['materials'] = []
        
        # 加载成品数据
        products_path = os.path.join(self.json_data_path, 'products', 'index.json')
        if os.path.exists(products_path):
            with open(products_path, 'r', encoding='utf-8') as f:
                data['products'] = json.load(f)
        else:
            data['products'] = []
        
        return data
    
    def migrate_base_materials(self, base_data: List[Dict[str, Any]]) -> Dict[int, int]:
        """迁移原材料数据，返回旧ID到新ID的映射"""
        id_mapping = {}
        
        print(f"开始迁移 {len(base_data)} 个原材料...")
        
        for item in base_data:
            old_id = item['id']
            name = item['name']
            
            # 检查是否已存在
            existing = self.db_manager.get_base_material_by_name(name)
            if existing:
                id_mapping[old_id] = existing['id']
                print(f"原材料 '{name}' 已存在，跳过")
                continue
            
            # 添加新的原材料
            new_id = self.db_manager.add_base_material(name)
            id_mapping[old_id] = new_id
            print(f"迁移原材料: {name} (旧ID: {old_id} -> 新ID: {new_id})")
        
        return id_mapping
    
    def migrate_materials(self, materials_data: List[Dict[str, Any]], 
                         base_id_mapping: Dict[int, int]) -> Dict[int, int]:
        """迁移半成品数据，返回旧ID到新ID的映射"""
        id_mapping = {}
        
        print(f"开始迁移 {len(materials_data)} 个半成品...")
        
        for item in materials_data:
            old_id = item['id']
            name = item['name']
            output_quantity = item.get('output', 1)
            
            # 检查是否已存在
            existing = self.db_manager.get_material_by_name(name)
            if existing:
                id_mapping[old_id] = existing['id']
                print(f"半成品 '{name}' 已存在，跳过")
                continue
            
            # 添加新的半成品
            new_id = self.db_manager.add_material(name, output_quantity)
            id_mapping[old_id] = new_id
            print(f"迁移半成品: {name} (旧ID: {old_id} -> 新ID: {new_id})")
            
            # 迁移配方需求
            if 'requirements' in item:
                self._migrate_requirements('material', new_id, item['requirements'], 
                                         base_id_mapping, id_mapping)
        
        return id_mapping
    
    def migrate_products(self, products_data: List[Dict[str, Any]], 
                        base_id_mapping: Dict[int, int], 
                        materials_id_mapping: Dict[int, int]) -> Dict[int, int]:
        """迁移成品数据，返回旧ID到新ID的映射"""
        id_mapping = {}
        
        print(f"开始迁移 {len(products_data)} 个成品...")
        
        for item in products_data:
            old_id = item['id']
            name = item['name']
            output_quantity = item.get('output', 1)
            
            # 检查是否已存在
            existing = self.db_manager.get_product_by_name(name)
            if existing:
                id_mapping[old_id] = existing['id']
                print(f"成品 '{name}' 已存在，跳过")
                continue
            
            # 添加新的成品
            new_id = self.db_manager.add_product(name, output_quantity)
            id_mapping[old_id] = new_id
            print(f"迁移成品: {name} (旧ID: {old_id} -> 新ID: {new_id})")
            
            # 迁移配方需求
            if 'requirements' in item:
                self._migrate_requirements('product', new_id, item['requirements'], 
                                         base_id_mapping, materials_id_mapping)
        
        return id_mapping
    
    def _migrate_requirements(self, recipe_type: str, recipe_id: int, 
                            requirements: List[Dict[str, Any]], 
                            base_id_mapping: Dict[int, int], 
                            materials_id_mapping: Dict[int, int]):
        """迁移配方需求"""
        for req in requirements:
            quantity = req['quantity']
            
            if 'base_id' in req:
                # 原材料需求
                old_base_id = req['base_id']
                if old_base_id in base_id_mapping:
                    new_base_id = base_id_mapping[old_base_id]
                    self.db_manager.add_recipe_requirement(
                        recipe_type, recipe_id, 'base', new_base_id, quantity
                    )
                else:
                    print(f"警告: 找不到原材料ID {old_base_id} 的映射")
            
            elif 'material_id' in req:
                # 半成品需求
                old_material_id = req['material_id']
                if old_material_id in materials_id_mapping:
                    new_material_id = materials_id_mapping[old_material_id]
                    self.db_manager.add_recipe_requirement(
                        recipe_type, recipe_id, 'material', new_material_id, quantity
                    )
                else:
                    print(f"警告: 找不到半成品ID {old_material_id} 的映射")
    
    def migrate_all(self) -> bool:
        """执行完整的数据迁移"""
        try:
            print("开始数据迁移...")
            
            # 加载JSON数据
            json_data = self.load_json_data()
            
            # 按顺序迁移数据（原材料 -> 半成品 -> 成品）
            base_id_mapping = self.migrate_base_materials(json_data['base'])
            materials_id_mapping = self.migrate_materials(json_data['materials'], base_id_mapping)
            products_id_mapping = self.migrate_products(json_data['products'], 
                                                       base_id_mapping, materials_id_mapping)
            
            print("数据迁移完成！")
            print(f"迁移统计:")
            print(f"  原材料: {len(base_id_mapping)} 个")
            print(f"  半成品: {len(materials_id_mapping)} 个")
            print(f"  成品: {len(products_id_mapping)} 个")
            
            return True
            
        except Exception as e:
            print(f"数据迁移失败: {e}")
            return False
    
    def backup_json_data(self, backup_path: str = None):
        """备份原始JSON数据"""
        if backup_path is None:
            backup_path = os.path.join(os.path.dirname(self.json_data_path), 'data_backup')
        
        os.makedirs(backup_path, exist_ok=True)
        
        # 复制所有JSON文件
        import shutil
        
        for subdir in ['base', 'materials', 'products']:
            src_dir = os.path.join(self.json_data_path, subdir)
            dst_dir = os.path.join(backup_path, subdir)
            
            if os.path.exists(src_dir):
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
        
        print(f"JSON数据已备份到: {backup_path}")
    
    def verify_migration(self) -> bool:
        """验证迁移结果"""
        try:
            json_data = self.load_json_data()
            
            # 验证数量
            db_base_count = len(self.db_manager.get_base_materials())
            db_materials_count = len(self.db_manager.get_materials())
            db_products_count = len(self.db_manager.get_products())
            
            json_base_count = len(json_data['base'])
            json_materials_count = len(json_data['materials'])
            json_products_count = len(json_data['products'])
            
            print("迁移验证结果:")
            print(f"原材料: JSON({json_base_count}) -> DB({db_base_count})")
            print(f"半成品: JSON({json_materials_count}) -> DB({db_materials_count})")
            print(f"成品: JSON({json_products_count}) -> DB({db_products_count})")
            
            # 检查是否有数据丢失
            if (db_base_count >= json_base_count and 
                db_materials_count >= json_materials_count and 
                db_products_count >= json_products_count):
                print("✓ 迁移验证通过")
                return True
            else:
                print("✗ 迁移验证失败，可能有数据丢失")
                return False
                
        except Exception as e:
            print(f"验证失败: {e}")
            return False


if __name__ == "__main__":
    # 独立运行时执行迁移
    migrator = DataMigrator()
    
    # 备份原始数据
    migrator.backup_json_data()
    
    # 执行迁移
    if migrator.migrate_all():
        # 验证迁移结果
        migrator.verify_migration()
    else:
        print("迁移失败，请检查错误信息")