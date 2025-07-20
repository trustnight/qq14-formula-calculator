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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建半成品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    output_quantity INTEGER DEFAULT 1,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建成品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    output_quantity INTEGER DEFAULT 1,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
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
    def add_base_material(self, name: str, description: str = None) -> int:
        """添加原材料"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO base_materials (name, description) VALUES (?, ?)',
                (name, description)
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
    
    def update_base_material(self, material_id: int, name: str, description: str = None):
        """更新原材料名称和描述"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE base_materials SET name = ?, description = ? WHERE id = ?',
                (name, description, material_id)
            )
            conn.commit()
    
    # 半成品操作
    def add_material(self, name: str, output_quantity: int = 1, description: str = None) -> int:
        """添加半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO materials (name, output_quantity, description) VALUES (?, ?, ?)',
                (name, output_quantity, description)
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
    
    def update_material(self, material_id: int, name: str, output_quantity: int = 1, description: str = None):
        """更新半成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE materials SET name = ?, output_quantity = ?, description = ? WHERE id = ?',
                (name, output_quantity, description, material_id)
            )
            conn.commit()
    
    # 成品操作
    def add_product(self, name: str, output_quantity: int = 1, description: str = None) -> int:
        """添加成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO products (name, output_quantity, description) VALUES (?, ?, ?)',
                (name, output_quantity, description)
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
    
    def update_product(self, product_id: int, name: str, output_quantity: int = 1, description: str = None):
        """更新成品"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE products SET name = ?, output_quantity = ?, description = ? WHERE id = ?',
                (name, output_quantity, description, product_id)
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
        stats = {
            'base_materials': 0,
            'materials': 0,
            'products': 0,
            'recipe_requirements': 0
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 统计原材料数量
            cursor.execute('SELECT COUNT(*) FROM base_materials')
            stats['base_materials'] = cursor.fetchone()[0]
            
            # 统计半成品数量
            cursor.execute('SELECT COUNT(*) FROM materials')
            stats['materials'] = cursor.fetchone()[0]
            
            # 统计成品数量
            cursor.execute('SELECT COUNT(*) FROM products')
            stats['products'] = cursor.fetchone()[0]
            
            # 统计配方需求数量
            cursor.execute('SELECT COUNT(*) FROM recipe_requirements')
            stats['recipe_requirements'] = cursor.fetchone()[0]
        
        return stats