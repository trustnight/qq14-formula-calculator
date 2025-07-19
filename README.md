# FFXIV 配方计算器

![声明](image/README/1752901666285.png)

一个用于《最终幻想XIV》的配方材料需求计算工具，支持复杂的多层级配方计算和批量管理。

## 项目概述

本项目是一个基于 Python 和 PySide6 开发的桌面应用程序，专门用于计算《最终幻想XIV》游戏中的配方材料需求。支持原材料、半成品和成品的管理，能够自动计算复杂配方的基础材料需求，并提供直观的用户界面。

## 功能特性

- 🧮 **智能配方计算**: 自动计算多层级配方的基础材料需求
- 📊 **批量计算**: 支持同时计算多个物品的材料需求
- 🗃️ **数据管理**: 完整的原材料、半成品、成品管理系统
- 📁 **CSV导入导出**: 支持CSV格式的数据批量导入和导出
- 🎨 **现代化UI**: 支持Fluent Design风格界面（可选）
- 🔍 **搜索过滤**: 快速搜索和筛选物品
- 🌳 **配方树**: 可视化显示配方分解结构
- 💾 **数据迁移**: 支持从JSON格式迁移数据

## 项目结构

```
ffixv-cw-calculate/
├── src/                    # 源代码目录
│   ├── core/              # 核心业务逻辑
│   │   ├── calculator.py  # 配方计算引擎
│   │   ├── database.py    # 数据库管理
│   │   ├── csv_importer.py # CSV导入导出
│   │   └── data_migrator.py # 数据迁移工具
│   ├── gui/               # 图形用户界面
│   │   ├── __init__.py
│   │   └── main_window.py # 主窗口界面
│   ├── database/          # 数据库文件目录
│   └── main.py           # 程序入口
├── icon/                  # 图标资源
├── requirements.txt       # 项目依赖
└── README.md             # 项目说明文档
```

## 详细代码结构

### 核心模块 (src/core/)

#### 1. calculator.py - 配方计算引擎

**BOMCalculator 类**
- **功能**: 核心计算引擎，负责配方的材料需求计算
- **主要方法**:
  - `__init__(db_manager)`: 初始化计算器，接收数据库管理器实例
  - `calculate_by_name(item_name, quantity, item_type)`: 根据物品名称计算材料需求
  - `calculate_by_id(item_id, quantity, item_type)`: 根据物品ID计算材料需求
  - `_calculate(item_id, quantity, item_type, calculated_items)`: 递归计算核心方法
  - `calculate_multiple_items(items)`: 批量计算多个物品的材料需求
  - `get_recipe_tree(item_name, quantity, item_type)`: 获取配方分解树结构
  - `format_requirements_for_display(requirements)`: 格式化计算结果用于显示
  - `get_item_info(item_id, item_type)`: 获取物品详细信息

#### 2. database.py - 数据库管理

**DatabaseManager 类**
- **功能**: SQLite数据库的创建、连接和所有数据操作
- **数据表结构**:
  - `base_materials`: 原材料表 (id, name, description)
  - `materials`: 半成品表 (id, name, output_quantity, description)
  - `products`: 成品表 (id, name, output_quantity, description)
  - `recipe_requirements`: 配方需求表 (id, recipe_type, recipe_id, ingredient_type, ingredient_id, quantity)
- **主要方法**:
  - `__init__(db_path)`: 初始化数据库连接
  - `init_database()`: 创建数据库表结构
  - **原材料操作**:
    - `add_base_material(name, description)`: 添加原材料
    - `get_base_materials()`: 获取所有原材料
    - `get_base_material_by_id(material_id)`: 根据ID获取原材料
    - `get_base_material_by_name(name)`: 根据名称获取原材料
    - `delete_base_material(material_id)`: 删除原材料
  - **半成品操作**:
    - `add_material(name, output_quantity, description)`: 添加半成品
    - `get_materials()`: 获取所有半成品
    - `get_material_by_id(material_id)`: 根据ID获取半成品
    - `get_material_by_name(name)`: 根据名称获取半成品
    - `delete_material(material_id)`: 删除半成品
  - **成品操作**:
    - `add_product(name, output_quantity, description)`: 添加成品
    - `get_products()`: 获取所有成品
    - `get_product_by_id(product_id)`: 根据ID获取成品
    - `get_product_by_name(name)`: 根据名称获取成品
    - `delete_product(product_id)`: 删除成品
  - **配方需求操作**:
    - `add_recipe_requirement(recipe_type, recipe_id, ingredient_type, ingredient_id, quantity)`: 添加配方需求
    - `get_recipe_requirements(recipe_type, recipe_id)`: 获取配方需求
    - `delete_recipe_requirements(recipe_type, recipe_id)`: 删除配方需求
  - **通用操作**:
    - `search_all_items(keyword)`: 搜索所有类型物品
    - `clear_all_data()`: 清空所有数据
    - `get_statistics()`: 获取数据统计信息

#### 3. csv_importer.py - CSV导入导出工具

**CSVImporter 类**
- **功能**: 处理CSV格式的数据导入和导出
- **主要方法**:
  - `__init__(db_manager)`: 初始化，接收数据库管理器实例
  - **导入方法**:
    - `import_base_materials_from_csv(csv_file_path)`: 从CSV导入原材料
    - `import_materials_from_csv(csv_file_path)`: 从CSV导入半成品
    - `import_products_from_csv(csv_file_path)`: 从CSV导入成品
    - `_process_recipe_requirements(row, recipe_type, recipe_id)`: 处理配方需求数据
  - **导出方法**:
    - `export_base_materials_to_csv(csv_file_path)`: 导出原材料到CSV
    - `export_materials_to_csv(csv_file_path)`: 导出半成品到CSV
    - `export_products_to_csv(csv_file_path)`: 导出成品到CSV
    - `_get_ingredient_name(ingredient_type, ingredient_id)`: 获取成分名称
  - **模板创建**:
    - `create_csv_templates(output_dir)`: 创建CSV导入模板文件

#### 4. data_migrator.py - 数据迁移工具

**DataMigrator 类**
- **功能**: 将JSON格式的历史数据迁移到SQLite数据库
- **主要方法**:
  - `__init__(db_manager, json_data_path)`: 初始化迁移工具
  - `load_json_data()`: 加载所有JSON数据文件
  - `migrate_base_materials(base_data)`: 迁移原材料数据
  - `migrate_materials(materials_data, base_id_mapping)`: 迁移半成品数据
  - `migrate_products(products_data, base_id_mapping, materials_id_mapping)`: 迁移成品数据
  - `_migrate_requirements(recipe_type, recipe_id, requirements, base_id_mapping, materials_id_mapping)`: 迁移配方需求
  - `migrate_all()`: 执行完整的数据迁移流程
  - `backup_json_data(backup_path)`: 备份原始JSON数据

### 图形界面模块 (src/gui/)

#### main_window.py - 主窗口界面

**工作线程类**:

1. **CalculationWorker 类**
   - **功能**: 后台计算工作线程，避免界面冻结
   - **信号**: `finished(dict)`, `error(str)`
   - **方法**: `run()` - 执行计算任务

2. **ImportWorker 类**
   - **功能**: CSV导入工作线程
   - **信号**: `finished(dict)`, `error(str)`, `progress(str)`
   - **方法**: `run()` - 执行导入任务

**主窗口类**:

**FFXIVCalculatorWindow 类**
- **继承**: `FluentWindow`（如果可用）或 `QMainWindow`
- **功能**: 应用程序主窗口，整合所有功能模块
- **主要属性**:
  - `db_manager`: 数据库管理器实例
  - `calculator`: 配方计算器实例
  - `csv_importer`: CSV导入器实例
  - `selected_items`: 当前选中的配方列表

- **界面初始化方法**:
  - `__init__()`: 初始化主窗口和所有组件
  - `init_ui()`: 初始化用户界面
  - `init_fluent_ui()`: 初始化Fluent Design界面
  - `init_standard_ui()`: 初始化标准界面

- **页面创建方法**:
  - `create_calculator_page()`: 创建计算器页面
  - `create_recipe_selection_widget()`: 创建配方选择组件
  - `create_calculation_result_widget()`: 创建计算结果显示组件
  - `create_recipe_management_page()`: 创建配方管理页面
  - `create_recipe_menu_widget()`: 创建配方管理菜单
  - `create_recipe_content_widget()`: 创建配方内容区域

- **数据操作方法**:
  - `load_data()`: 加载初始数据
  - `refresh_item_list()`: 刷新物品列表
  - `refresh_recipe_list()`: 刷新配方列表
  - `refresh_selected_items()`: 刷新选中物品列表
  - `ensure_sample_data()`: 确保有示例数据

- **计算功能方法**:
  - `add_selected_item()`: 添加选中物品到计算列表
  - `remove_selected_item(index)`: 从计算列表移除物品
  - `calculate_requirements()`: 执行材料需求计算
  - `on_calculation_finished(result)`: 处理计算完成事件
  - `on_calculation_error(error)`: 处理计算错误事件
  - `display_calculation_results(requirements, raw_result)`: 显示计算结果
  - `build_recipe_tree(tree_data)`: 构建配方分解树

- **配方管理方法**:
  - `on_recipe_type_changed()`: 配方类型切换事件
  - `on_recipe_selected()`: 配方选择事件
  - `add_new_recipe()`: 添加新配方
  - `save_current_recipe()`: 保存当前配方
  - `delete_selected_recipes()`: 删除选中的配方
  - `add_requirement()`: 添加配方需求
  - `remove_requirement(index)`: 移除配方需求
  - `refresh_requirements_table()`: 刷新需求表格

- **数据导入导出方法**:
  - `import_csv_data()`: 导入CSV数据
  - `export_csv_data()`: 导出CSV数据
  - `create_csv_templates()`: 创建CSV模板
  - `import_recipes_from_json(file_path)`: 从JSON导入配方
  - `migrate_data_from_json()`: 从JSON迁移数据

- **界面事件处理方法**:
  - `on_search_changed()`: 搜索框变化事件
  - `on_type_changed()`: 类型选择变化事件
  - `on_item_double_clicked(item)`: 物品双击事件
  - `on_page_changed(index)`: 页面切换事件
  - `show_message(message, msg_type)`: 显示消息提示
  - `format_number(number)`: 格式化数字显示

- **数据管理方法**:
  - `clear_all_data()`: 清空所有数据
  - `backup_database()`: 备份数据库
  - `restore_database()`: 恢复数据库

**全局函数**:
- `main()`: 应用程序入口函数，创建QApplication和主窗口

### 程序入口 (src/main.py)

简单的程序启动脚本，导入并调用GUI模块的main函数。

## 安装和运行

### 环境要求

- Python 3.8+
- PySide6 6.5.0+
- pandas 1.5.0+
- openpyxl 3.1.0+
- PySide6-Fluent-Widgets 1.1.0+（可选，用于现代化UI）

### 安装步骤

1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行程序：
   ```bash
   cd src
   python main.py
   ```

### CSV数据格式

#### 原材料CSV格式
```csv
name,description
示例原材料,这是一个示例描述
```

#### 半成品/成品CSV格式
```csv
name,output_quantity,description,ingredient_type_1,ingredient_name_1,quantity_1,ingredient_type_2,ingredient_name_2,quantity_2
示例半成品,1,这是一个示例半成品,base,示例原材料1,2,base,示例原材料2,1
```

## 技术特点

1. **模块化设计**: 核心逻辑与界面分离，便于维护和扩展
2. **多线程处理**: 计算和导入操作在后台线程执行，保持界面响应
3. **灵活的UI框架**: 支持标准Qt界面和现代化Fluent Design界面
4. **完整的数据管理**: 支持增删改查、导入导出、数据迁移等完整功能
5. **递归计算算法**: 智能处理多层级配方依赖关系
6. **用户友好**: 直观的界面设计和完善的错误处理

## 开发说明

本项目采用面向对象的设计模式，各个模块职责明确：
- `core`模块负责业务逻辑和数据处理
- `gui`模块负责用户界面和交互
- 通过依赖注入的方式实现模块间的解耦

代码遵循Python PEP 8规范，包含详细的中文注释，便于理解和维护。

## 许可证

本项目仅供学习和个人使用。