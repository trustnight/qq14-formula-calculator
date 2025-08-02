import sys
import os
import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseManager:
    """数据库管理类，负责SQLite数据库的创建、连接和操作"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = os.path.join(os.getcwd(), 'ffixv_recipes.db')
        else:
            self.db_path = db_path
        # 不再创建任何目录
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以像字典一样访问
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建原材料表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS base_materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    cost REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 检查并添加cost字段（用于数据库迁移）
            cursor.execute("PRAGMA table_info(base_materials)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'cost' not in columns:
                cursor.execute('ALTER TABLE base_materials ADD COLUMN cost REAL DEFAULT 0.0')
            
            # 创建半成品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    output_quantity INTEGER DEFAULT 1,
                    description TEXT,
                    price REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 检查并添加price字段（用于数据库迁移）
            cursor.execute("PRAGMA table_info(materials)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'price' not in columns:
                cursor.execute('ALTER TABLE materials ADD COLUMN price REAL DEFAULT 0.0')
            
            # 创建成品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    output_quantity INTEGER DEFAULT 1,
                    description TEXT,
                    price REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 检查并添加price字段（用于数据库迁移）
            cursor.execute("PRAGMA table_info(products)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'price' not in columns:
                cursor.execute('ALTER TABLE products ADD COLUMN price REAL DEFAULT 0.0')
            
            # 创建配方需求表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recipe_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_type TEXT NOT NULL CHECK(recipe_type IN ('material', 'product')),
                    recipe_id INTEGER NOT NULL,
                    ingredient_type TEXT NOT NULL CHECK(ingredient_type IN ('base', 'material')),
                    ingredient_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建设置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_recipe_requirements_recipe 
                ON recipe_requirements(recipe_type, recipe_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_recipe_requirements_ingredient 
                ON recipe_requirements(ingredient_type, ingredient_id)
            ''')
            
            conn.commit()
    
    # 原材料操作
    def add_base_material(self, name: str, description: str = None, cost: float = 0) -> int:
        """添加原材料"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO base_materials (name, description, cost) VALUES (?, ?, ?)',
                (name, description, cost)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_base_materials(self) -> List[Dict[str, Any]]:
        """获取所有原材料"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM base_materials ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_base_material_by_id(self, material_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取原材料"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM base_materials WHERE id = ?', (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_base_material_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取原材料"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM base_materials WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_base_material(self, material_id: int, name: str, description: str = None, cost: float = 0):
        """更新原材料名称、描述和单价"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE base_materials SET name = ?, description = ?, cost = ? WHERE id = ?',
                (name, description, cost, material_id)
            )
            conn.commit()
    
    # 半成品操作
    def add_material(self, name: str, output_quantity: int = 1, description: str = None, price: float = 0.0) -> int:
        """添加半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO materials (name, output_quantity, description, price) VALUES (?, ?, ?, ?)',
                (name, output_quantity, description, price)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_materials(self) -> List[Dict[str, Any]]:
        """获取所有半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_material_by_id(self, material_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE id = ?', (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_material_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_material(self, material_id: int, name: str, output_quantity: int = 1, description: str = None, price: float = 0.0):
        """更新半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE materials SET name = ?, output_quantity = ?, description = ?, price = ? WHERE id = ?',
                (name, output_quantity, description, price, material_id)
            )
            conn.commit()
    
    # 成品操作
    def add_product(self, name: str, output_quantity: int = 1, description: str = None, price: float = 0.0) -> int:
        """添加成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO products (name, output_quantity, description, price) VALUES (?, ?, ?, ?)',
                (name, output_quantity, description, price)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_products(self) -> List[Dict[str, Any]]:
        """获取所有成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE name = ?', (name,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_product(self, product_id: int, name: str, output_quantity: int = 1, description: str = None, price: float = 0.0):
        """更新成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE products SET name = ?, output_quantity = ?, description = ?, price = ? WHERE id = ?',
                (name, output_quantity, description, price, product_id)
            )
            conn.commit()
    
    # 配方需求操作
    def add_recipe_requirement(self, recipe_type: str, recipe_id: int, 
                             ingredient_type: str, ingredient_id: int, quantity: float):
        """添加配方需求"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO recipe_requirements 
                   (recipe_type, recipe_id, ingredient_type, ingredient_id, quantity) 
                   VALUES (?, ?, ?, ?, ?)''',
                (recipe_type, recipe_id, ingredient_type, ingredient_id, quantity)
            )
            conn.commit()
    
    def get_recipe_requirements(self, recipe_type: str, recipe_id: int) -> List[Dict[str, Any]]:
        """获取配方需求"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM recipe_requirements 
                   WHERE recipe_type = ? AND recipe_id = ?''',
                (recipe_type, recipe_id)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_recipe_requirements(self, recipe_type: str, recipe_id: int):
        """删除配方的所有需求"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM recipe_requirements WHERE recipe_type = ? AND recipe_id = ?',
                (recipe_type, recipe_id)
            )
            conn.commit()
    
    # 删除操作
    def delete_base_material(self, material_id: int):
        """删除原材料"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM base_materials WHERE id = ?', (material_id,))
            conn.commit()
    
    def delete_material(self, material_id: int):
        """删除半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 先删除相关的配方需求
            cursor.execute(
                'DELETE FROM recipe_requirements WHERE recipe_type = "material" AND recipe_id = ?',
                (material_id,)
            )
            # 删除半成品
            cursor.execute('DELETE FROM materials WHERE id = ?', (material_id,))
            conn.commit()
    
    def delete_product(self, product_id: int):
        """删除成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 先删除相关的配方需求
            cursor.execute(
                'DELETE FROM recipe_requirements WHERE recipe_type = "product" AND recipe_id = ?',
                (product_id,)
            )
            # 删除成品
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            conn.commit()
    
    def search_items(self, keyword: str) -> Dict[str, List[Dict[str, Any]]]:
        """搜索所有类型的物品"""
        result = {
            'base_materials': [],
            'materials': [],
            'products': []
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 搜索原材料
            cursor.execute(
                'SELECT * FROM base_materials WHERE name LIKE ? ORDER BY name',
                (f'%{keyword}%',)
            )
            result['base_materials'] = [dict(row) for row in cursor.fetchall()]
            
            # 搜索半成品
            cursor.execute(
                'SELECT * FROM materials WHERE name LIKE ? ORDER BY name',
                (f'%{keyword}%',)
            )
            result['materials'] = [dict(row) for row in cursor.fetchall()]
            
            # 搜索成品
            cursor.execute(
                'SELECT * FROM products WHERE name LIKE ? ORDER BY name',
                (f'%{keyword}%',)
            )
            result['products'] = [dict(row) for row in cursor.fetchall()]
        
        return result
    
    def clear_all_data(self):
        """清空所有数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 删除所有配方需求
            cursor.execute('DELETE FROM recipe_requirements')
            # 删除所有成品
            cursor.execute('DELETE FROM products')
            # 删除所有半成品
            cursor.execute('DELETE FROM materials')
            # 删除所有原材料
            cursor.execute('DELETE FROM base_materials')
            conn.commit()
    
    def get_data_statistics(self) -> Dict[str, int]:
        """获取数据统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 统计各类数据数量
            cursor.execute('SELECT COUNT(*) FROM base_materials')
            base_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM materials')
            material_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM products')
            product_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM recipe_requirements')
            recipe_count = cursor.fetchone()[0]
            
        stats = {
            'base_materials': base_count,
            'materials': material_count,
            'products': product_count,
            'recipes': recipe_count
        }
        
        return stats
    
    def get_recipes_using_ingredient(self, ingredient_type: str, ingredient_id: int) -> List[Dict[str, Any]]:
        """获取使用指定原材料或半成品的配方列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 查询使用该原料的配方
            cursor.execute('''
                SELECT DISTINCT rr.recipe_type, rr.recipe_id, rr.quantity
                FROM recipe_requirements rr
                WHERE rr.ingredient_type = ? AND rr.ingredient_id = ?
                ORDER BY rr.recipe_type, rr.recipe_id
            ''', (ingredient_type, ingredient_id))
            
            recipe_refs = cursor.fetchall()
            recipes = []
            
            for recipe_ref in recipe_refs:
                recipe_type = recipe_ref['recipe_type']
                recipe_id = recipe_ref['recipe_id']
                quantity_needed = recipe_ref['quantity']
                
                # 根据配方类型获取配方详情
                if recipe_type == 'material':
                    cursor.execute('SELECT * FROM materials WHERE id = ?', (recipe_id,))
                    recipe_data = cursor.fetchone()
                    if recipe_data:
                        recipes.append({
                            'type': '半成品',
                            'name': recipe_data['name'],
                            'output_quantity': recipe_data['output_quantity'],
                            'quantity_needed': quantity_needed,
                            'recipe_type': recipe_type,
                            'recipe_id': recipe_id
                        })
                elif recipe_type == 'product':
                    cursor.execute('SELECT * FROM products WHERE id = ?', (recipe_id,))
                    recipe_data = cursor.fetchone()
                    if recipe_data:
                        recipes.append({
                            'type': '成品',
                            'name': recipe_data['name'],
                            'output_quantity': recipe_data['output_quantity'],
                            'quantity_needed': quantity_needed,
                            'recipe_type': recipe_type,
                            'recipe_id': recipe_id
                        })
            
            return recipes
    
    # 设置操作
    def set_setting(self, key: str, value: str):
        """设置配置项"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
                (key, value)
            )
            conn.commit()
    
    def get_setting(self, key: str, default_value: str = None) -> str:
        """获取配置项"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row[0] if row else default_value
    
    def get_tax_rate(self) -> float:
        """获取交易税率"""
        tax_rate_str = self.get_setting('tax_rate', '5.0')
        try:
            return float(tax_rate_str)
        except ValueError:
            return 5.0
    
    def set_tax_rate(self, tax_rate: float):
        """设置交易税率"""
        self.set_setting('tax_rate', str(tax_rate))