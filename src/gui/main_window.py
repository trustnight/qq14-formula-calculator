import sys
import os
from typing import Dict, List, Any, Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QFileDialog, QProgressBar, QSplitter, QGroupBox,
    QHeaderView, QAbstractItemView, QInputDialog, QDialog, QSizePolicy,
    QListWidget, QListWidgetItem, QScrollArea, QFrame, QDialogButtonBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor

try:
    from qfluentwidgets import (
        FluentWindow, NavigationItemPosition, FluentIcon,
        PrimaryPushButton, PushButton, LineEdit, SpinBox, ComboBox,
        TableWidget, TreeWidget, MessageBox, ProgressBar,
        CardWidget, HeaderCardWidget, SimpleCardWidget,
        InfoBar, InfoBarPosition
    )
    FLUENT_AVAILABLE = True
except ImportError:
    FLUENT_AVAILABLE = False

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseManager
from core.calculator import BOMCalculator
from core.csv_importer import CSVImporter
from core.data_migrator import DataMigrator


class CalculationWorker(QThread):
    """计算工作线程"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, calculator: BOMCalculator, items: List[Dict[str, Any]]):
        super().__init__()
        self.calculator = calculator
        self.items = items
    
    def run(self):
        try:
            result = self.calculator.calculate_multiple_items(self.items)
            formatted_result = self.calculator.format_requirements_for_display(result)
            self.finished.emit({'requirements': formatted_result, 'raw': result})
        except Exception as e:
            self.error.emit(str(e))


class ImportWorker(QThread):
    """CSV导入工作线程"""
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, csv_importer, file_path: str):
        super().__init__()
        self.csv_importer = csv_importer
        self.file_path = file_path
    
    def run(self):
        try:
            self.progress.emit("正在导入CSV数据...")
            result = self.csv_importer.import_from_csv(self.file_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CreateMissingItemDialog(QDialog):
    """创建缺失物品对话框"""
    
    def __init__(self, parent, db_manager, item_name, item_type):
        super().__init__(parent)
        self.db_manager = db_manager
        self.item_name = item_name
        self.item_type = item_type
        self.setWindowTitle(f"创建{item_type}: {item_name}")
        self.setMinimumSize(400, 300)
        self.resize(500, 400)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 提示信息
        info_label = QLabel(f"未检测到{self.item_type} '{self.item_name}'，请添加其配方需求：")
        info_label.setStyleSheet("font-weight: bold; color: #d63031; margin: 10px;")
        layout.addWidget(info_label)
        
        # 产出数量
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("产出数量:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999)
        self.quantity_spin.setValue(1)
        quantity_layout.addWidget(self.quantity_spin)
        layout.addLayout(quantity_layout)
        
        # 配方需求
        requirements_group = QGroupBox("配方需求")
        requirements_layout = QVBoxLayout(requirements_group)
        
        # 添加需求的控件
        add_req_layout = QHBoxLayout()
        add_req_layout.addWidget(QLabel("添加需求:"))
        
        # 半成品只能添加原材料
        self.req_name_combo = QComboBox()
        self.req_name_combo.setEditable(True)
        add_req_layout.addWidget(self.req_name_combo)
        
        self.req_quantity_spin = QSpinBox()
        self.req_quantity_spin.setRange(1, 999)
        self.req_quantity_spin.setValue(1)
        add_req_layout.addWidget(self.req_quantity_spin)
        
        add_req_btn = QPushButton("添加")
        add_req_btn.clicked.connect(self.add_requirement)
        add_req_layout.addWidget(add_req_btn)
        
        requirements_layout.addLayout(add_req_layout)
        
        # 需求列表
        self.requirements_list = QListWidget()
        requirements_layout.addWidget(self.requirements_list)
        
        # 删除需求按钮
        remove_req_btn = QPushButton("删除选中需求")
        remove_req_btn.clicked.connect(self.remove_requirement)
        requirements_layout.addWidget(remove_req_btn)
        
        layout.addWidget(requirements_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_creation)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 初始化数据
        self.update_requirement_options()
    
    def update_requirement_options(self):
        """更新需求选项"""
        self.req_name_combo.clear()
        base_materials = self.db_manager.get_base_materials()
        for material in base_materials:
            self.req_name_combo.addItem(material['name'])
    
    def add_requirement(self):
        """添加配方需求"""
        req_name = self.req_name_combo.currentText().strip()
        req_quantity = self.req_quantity_spin.value()
        
        if not req_name:
            QMessageBox.warning(self, "警告", "请选择或输入原材料名称")
            return
        
        # 检查是否已存在
        for i in range(self.requirements_list.count()):
            item = self.requirements_list.item(i)
            if item.data(Qt.UserRole)['name'] == req_name:
                QMessageBox.warning(self, "警告", "该需求已存在")
                return
        
        # 添加到列表
        item_text = f"原材料: {req_name} x{req_quantity}"
        list_item = QListWidgetItem(item_text)
        list_item.setData(Qt.UserRole, {
            'name': req_name,
            'quantity': req_quantity
        })
        self.requirements_list.addItem(list_item)
    
    def remove_requirement(self):
        """删除选中的需求"""
        current_item = self.requirements_list.currentItem()
        if current_item:
            self.requirements_list.takeItem(self.requirements_list.row(current_item))
    
    def accept_creation(self):
        """确认创建物品"""
        output_quantity = self.quantity_spin.value()
        
        # 收集需求
        requirements = []
        for i in range(self.requirements_list.count()):
            item = self.requirements_list.item(i)
            req_data = item.data(Qt.UserRole)
            requirements.append(req_data)
        
        # 检查原材料是否存在，不存在则创建
        for req in requirements:
            base_material = self.db_manager.get_base_material_by_name(req['name'])
            if not base_material:
                reply = QMessageBox.question(
                    self, "缺少原材料", 
                    f"未检测到原材料 '{req['name']}'，是否创建？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    try:
                        self.db_manager.add_base_material(req['name'])
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"创建原材料失败: {str(e)}")
                        return
                else:
                    return
        
        try:
            # 创建半成品
            item_id = self.db_manager.add_material(self.item_name, output_quantity)
            
            # 添加配方需求
            for req in requirements:
                base_material = self.db_manager.get_base_material_by_name(req['name'])
                if base_material:
                    self.db_manager.add_recipe_requirement(
                        'material', item_id, 'base', base_material['id'], req['quantity']
                    )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建{self.item_type}失败: {str(e)}")


class RecipeAddDialog(QDialog):
    """分层级配方添加对话框"""
    
    def __init__(self, parent, db_manager, edit_mode=False, item_type=None, item_id=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.edit_mode = edit_mode
        self.item_type = item_type
        self.item_id = item_id
        
        if edit_mode:
            self.setWindowTitle("编辑配方")
        else:
            self.setWindowTitle("添加配方")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        self.init_ui()
        
        # 如果是编辑模式，加载现有数据
        if edit_mode and item_type and item_id:
            self.load_existing_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 第一步：基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout(basic_group)
        
        # 配方名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("配方名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入配方名称")
        name_layout.addWidget(self.name_edit)
        basic_layout.addLayout(name_layout)
        
        # 配方类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("配方类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["成品", "半成品"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        basic_layout.addLayout(type_layout)
        
        # 产出数量
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("产出数量:"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 999)
        self.quantity_spin.setValue(1)
        quantity_layout.addWidget(self.quantity_spin)
        basic_layout.addLayout(quantity_layout)
        
        layout.addWidget(basic_group)
        
        # 第二步：配方需求
        requirements_group = QGroupBox("配方需求")
        requirements_layout = QVBoxLayout(requirements_group)
        
        # 添加需求的控件
        add_req_layout = QHBoxLayout()
        add_req_layout.addWidget(QLabel("添加需求:"))
        
        self.req_type_combo = QComboBox()
        self.req_type_combo.addItems(["原材料", "半成品"])
        add_req_layout.addWidget(self.req_type_combo)
        
        self.req_name_combo = QComboBox()
        self.req_name_combo.setEditable(True)
        add_req_layout.addWidget(self.req_name_combo)
        
        self.req_quantity_spin = QSpinBox()
        self.req_quantity_spin.setRange(1, 999)
        self.req_quantity_spin.setValue(1)
        add_req_layout.addWidget(self.req_quantity_spin)
        
        add_req_btn = QPushButton("添加")
        add_req_btn.clicked.connect(self.add_requirement)
        add_req_layout.addWidget(add_req_btn)
        
        requirements_layout.addLayout(add_req_layout)
        
        # 需求列表
        self.requirements_list = QListWidget()
        requirements_layout.addWidget(self.requirements_list)
        
        # 删除需求按钮
        remove_req_btn = QPushButton("删除选中需求")
        remove_req_btn.clicked.connect(self.remove_requirement)
        requirements_layout.addWidget(remove_req_btn)
        
        layout.addWidget(requirements_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_recipe)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 初始化数据
        self.update_requirement_options()
        self.on_type_changed()
    
    def on_type_changed(self):
        """配方类型改变时更新可选需求类型"""
        recipe_type = self.type_combo.currentText()
        self.req_type_combo.clear()
        
        if recipe_type == "成品":
            # 成品可以添加半成品和原材料
            self.req_type_combo.addItems(["原材料", "半成品"])
        else:  # 半成品
            # 半成品只能添加原材料
            self.req_type_combo.addItems(["原材料"])
        
        self.update_requirement_options()
    
    def update_requirement_options(self):
        """更新需求选项"""
        req_type = self.req_type_combo.currentText()
        self.req_name_combo.clear()
        
        if req_type == "原材料":
            base_materials = self.db_manager.get_base_materials()
            for material in base_materials:
                self.req_name_combo.addItem(material['name'])
        elif req_type == "半成品":
            materials = self.db_manager.get_materials()
            for material in materials:
                self.req_name_combo.addItem(material['name'])
        
        # 连接信号
        self.req_type_combo.currentTextChanged.connect(self.update_requirement_options)
    
    def add_requirement(self):
        """添加配方需求"""
        req_type = self.req_type_combo.currentText()
        req_name = self.req_name_combo.currentText().strip()
        req_quantity = self.req_quantity_spin.value()
        
        if not req_name:
            QMessageBox.warning(self, "警告", "请选择或输入物品名称")
            return
        
        # 检查是否已存在
        for i in range(self.requirements_list.count()):
            item = self.requirements_list.item(i)
            if item.data(Qt.UserRole)['name'] == req_name:
                QMessageBox.warning(self, "警告", "该需求已存在")
                return
        
        # 添加到列表
        item_text = f"{req_type}: {req_name} x{req_quantity}"
        list_item = QListWidgetItem(item_text)
        list_item.setData(Qt.UserRole, {
            'type': req_type,
            'name': req_name,
            'quantity': req_quantity
        })
        self.requirements_list.addItem(list_item)
    
    def remove_requirement(self):
        """删除选中的需求"""
        current_item = self.requirements_list.currentItem()
        if current_item:
            self.requirements_list.takeItem(self.requirements_list.row(current_item))
    
    def load_existing_data(self):
        """加载现有配方数据"""
        try:
            # 获取物品信息
            if self.item_type == 'material':
                item_info = self.db_manager.get_material_by_id(self.item_id)
                recipe_type = '半成品'
            else:
                item_info = self.db_manager.get_product_by_id(self.item_id)
                recipe_type = '成品'
            
            if not item_info:
                return
            
            # 填充基本信息
            self.name_edit.setText(item_info['name'])
            self.name_edit.setEnabled(False)  # 编辑模式下不允许修改名称
            
            # 设置类型
            type_index = self.type_combo.findText(recipe_type)
            if type_index >= 0:
                self.type_combo.setCurrentIndex(type_index)
            self.type_combo.setEnabled(False)  # 编辑模式下不允许修改类型
            
            # 设置产出数量
            self.quantity_spin.setValue(item_info['output_quantity'])
            
            # 加载配方需求
            requirements = self.db_manager.get_recipe_requirements(self.item_type, self.item_id)
            for req in requirements:
                # 确定需求类型和名称
                if req['ingredient_type'] == 'base':
                    req_type = '原材料'
                    req_item = self.db_manager.get_base_material_by_id(req['ingredient_id'])
                else:
                    req_type = '半成品'
                    req_item = self.db_manager.get_material_by_id(req['ingredient_id'])
                
                if req_item:
                    # 添加到需求列表
                    item_text = f"{req_type}: {req_item['name']} x{req['quantity']}"
                    list_item = QListWidgetItem(item_text)
                    list_item.setData(Qt.UserRole, {
                        'type': req_type,
                        'name': req_item['name'],
                        'quantity': req['quantity']
                    })
                    self.requirements_list.addItem(list_item)
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配方数据失败: {str(e)}")
    
    def accept_recipe(self):
        """确认添加/编辑配方"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入配方名称")
            return
        
        recipe_type = self.type_combo.currentText()
        output_quantity = self.quantity_spin.value()
        
        # 如果不是编辑模式，检查是否已存在同名配方
        if not self.edit_mode:
            if recipe_type == "半成品":
                existing_item = self.db_manager.get_material_by_name(name)
            else:
                existing_item = self.db_manager.get_product_by_name(name)
            
            if existing_item:
                QMessageBox.warning(self, "警告", f"已存在同名的{recipe_type} '{name}'，请使用不同的名称")
                return
        
        # 收集需求
        requirements = []
        for i in range(self.requirements_list.count()):
            item = self.requirements_list.item(i)
            req_data = item.data(Qt.UserRole)
            requirements.append(req_data)
        
        # 检查依赖是否存在，如果不存在则提示创建
        missing_items = []
        for req in requirements:
            req_type = "base" if req['type'] == "原材料" else "material"
            
            if req_type == "base":
                req_item = self.db_manager.get_base_material_by_name(req['name'])
            else:
                req_item = self.db_manager.get_material_by_name(req['name'])
            
            if not req_item:
                missing_items.append(req)
        
        # 如果有缺失的物品，提示用户创建
        if missing_items:
            for missing in missing_items:
                if missing['type'] == "原材料":
                    # 直接创建原材料
                    reply = QMessageBox.question(
                        self, "缺少原材料", 
                        f"未检测到原材料 '{missing['name']}'，是否创建？",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        try:
                            self.db_manager.add_base_material(missing['name'])
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"创建原材料失败: {str(e)}")
                            return
                    else:
                        return
                else:
                    # 创建半成品，需要弹出创建对话框
                    dialog = CreateMissingItemDialog(self, self.db_manager, missing['name'], "半成品")
                    if dialog.exec() != QDialog.Accepted:
                        return
        
        try:
            if self.edit_mode:
                # 编辑模式：更新现有物品
                item_id = self.item_id
                item_type = self.item_type
                
                # 更新物品信息
                if item_type == 'material':
                    self.db_manager.update_material(item_id, name, output_quantity)
                else:
                    self.db_manager.update_product(item_id, name, output_quantity)
                
                # 删除现有配方需求
                self.db_manager.delete_recipe_requirements(item_type, item_id)
            else:
                # 添加模式：创建新物品
                if recipe_type == "半成品":
                    item_id = self.db_manager.add_material(name, output_quantity)
                    item_type = 'material'
                else:
                    item_id = self.db_manager.add_product(name, output_quantity)
                    item_type = 'product'
            
            # 添加配方需求
            for req in requirements:
                req_type = "base" if req['type'] == "原材料" else "material"
                
                # 重新获取需求物品ID（可能刚创建）
                if req_type == "base":
                    req_item = self.db_manager.get_base_material_by_name(req['name'])
                else:
                    req_item = self.db_manager.get_material_by_name(req['name'])
                
                if req_item:
                    self.db_manager.add_recipe_requirement(
                        item_type, item_id, req_type, req_item['id'], req['quantity']
                    )
            
            self.accept()
            
        except Exception as e:
            action = "编辑" if self.edit_mode else "添加"
            QMessageBox.critical(self, "错误", f"{action}配方失败: {str(e)}")


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def migrate_all(self) -> Dict[str, Any]:
        """迁移所有数据"""
        try:
            # 这里可以实现从JSON文件迁移数据的逻辑
            # 目前返回一个示例结果
            return {
                'success': True,
                'migrated_counts': {
                    'base_materials': 0,
                    'materials': 0,
                    'products': 0
                }
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }


class FFXIVCalculatorWindow(FluentWindow if FLUENT_AVAILABLE else QMainWindow):
    """FFXIV配方计算器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.calculator = BOMCalculator(self.db_manager)
        self.csv_importer = CSVImporter(self.db_manager)
        
        self.selected_items = []  # 选中的配方列表
        
        self.current_selected_item = None  # 初始化当前选中物品
        self.init_ui()
        self.load_data()
    
    def format_number(self, number):
        """格式化数字显示：整数显示为整数，小数保留两位"""
        if isinstance(number, (int, float)):
            if number == int(number):
                return str(int(number))
            else:
                return f"{number:.2f}"
        return str(number)
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("FFXIV 配方计算器")
        self.setGeometry(100, 100, 1200, 800)
        
        if FLUENT_AVAILABLE:
            self.init_fluent_ui()
        else:
            self.init_standard_ui()
    
    def init_fluent_ui(self):
        """初始化Fluent Design界面"""
        # 设置导航栏宽度
        self.navigationInterface.setExpandWidth(200)  # 设置展开宽度为200px
        
        # 创建各个页面
        self.create_calculator_page()
        self.create_recipe_management_page()
        
        # 添加导航项
        self.addSubInterface(
            self.calculator_page, FluentIcon.COMMAND_PROMPT, "计算器"
        )
        self.addSubInterface(
            self.recipe_page, FluentIcon.BOOK_SHELF, "配方管理"
        )
        
        # 连接页面切换事件
        self.stackedWidget.currentChanged.connect(self.on_page_changed)
    
    def init_standard_ui(self):
        """初始化标准界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个页面
        self.create_calculator_page()
        self.create_recipe_management_page()
        
        # 添加标签页
        self.tab_widget.addTab(self.calculator_page, "计算器")
        self.tab_widget.addTab(self.recipe_page, "配方管理")
        
        # 连接页面切换事件
        self.tab_widget.currentChanged.connect(self.on_page_changed)
    
    def create_calculator_page(self):
        """创建计算器页面"""
        if FLUENT_AVAILABLE:
            self.calculator_page = QWidget()
        else:
            self.calculator_page = QWidget()
        
        self.calculator_page.setObjectName("calculator_page")
        
        layout = QHBoxLayout(self.calculator_page)
        
        # 左侧：配方选择和列表
        left_widget = self.create_recipe_selection_widget()
        
        # 右侧：计算结果
        right_widget = self.create_calculation_result_widget()
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def create_recipe_selection_widget(self):
        """创建配方选择组件"""
        if FLUENT_AVAILABLE:
            widget = SimpleCardWidget()
        else:
            widget = QGroupBox("配方选择")
        
        layout = QVBoxLayout(widget)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        
        if FLUENT_AVAILABLE:
            self.search_edit = LineEdit()
        else:
            self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入物品名称...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit)
        
        layout.addLayout(search_layout)
        
        # 物品类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        
        if FLUENT_AVAILABLE:
            self.type_combo = ComboBox()
        else:
            self.type_combo = QComboBox()
        self.type_combo.addItems(["成品", "半成品"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        
        layout.addLayout(type_layout)
        
        # 物品表格
        if FLUENT_AVAILABLE:
            self.item_table = TableWidget()
        else:
            self.item_table = QTableWidget()
        
        self.item_table.setColumnCount(3)
        self.item_table.setHorizontalHeaderLabels(["名称", "产出数量", "操作"])
        # 设置列宽
        self.item_table.setColumnWidth(0, 200)  # 名称列
        self.item_table.setColumnWidth(1, 80)   # 产出数量列
        self.item_table.setColumnWidth(2, 100)  # 操作列
        self.item_table.horizontalHeader().setStretchLastSection(False)
        self.item_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 设置为只读
        self.item_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 添加双击事件
        self.item_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        layout.addWidget(self.item_table)
        
        # 添加按钮
        if FLUENT_AVAILABLE:
            self.add_button = PrimaryPushButton("添加到计算列表")
        else:
            self.add_button = QPushButton("添加到计算列表")
        self.add_button.clicked.connect(self.add_selected_item)
        layout.addWidget(self.add_button)
        
        # 已选择的配方列表
        layout.addWidget(QLabel("已选择的配方:"))
        
        if FLUENT_AVAILABLE:
            self.selected_table = TableWidget()
        else:
            self.selected_table = QTableWidget()
        
        self.selected_table.setColumnCount(4)
        self.selected_table.setHorizontalHeaderLabels(["名称", "类型", "数量", "操作"])
        # 设置列宽
        self.selected_table.setColumnWidth(0, 150)  # 名称列
        self.selected_table.setColumnWidth(1, 80)   # 类型列
        self.selected_table.setColumnWidth(2, 80)   # 数量列
        self.selected_table.setColumnWidth(3, 80)   # 操作列
        self.selected_table.horizontalHeader().setStretchLastSection(False)
        
        layout.addWidget(self.selected_table)
        
        # 计算按钮
        if FLUENT_AVAILABLE:
            self.calculate_button = PrimaryPushButton("计算材料需求")
        else:
            self.calculate_button = QPushButton("计算材料需求")
        self.calculate_button.clicked.connect(self.calculate_requirements)
        layout.addWidget(self.calculate_button)
        
        return widget
    
    def create_calculation_result_widget(self):
        """创建计算结果显示组件"""
        if FLUENT_AVAILABLE:
            widget = SimpleCardWidget()
        else:
            widget = QGroupBox("计算结果")
        
        layout = QVBoxLayout(widget)
        
        # 结果标题
        self.result_label = QLabel("计算结果将在这里显示")
        self.result_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(self.result_label)
        
        # 结果表格
        if FLUENT_AVAILABLE:
            self.result_table = TableWidget()
        else:
            self.result_table = QTableWidget()
        
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["材料名称", "需要数量"])
        # 设置列宽 - 让最后一列自动拉伸填满
        self.result_table.setColumnWidth(0, 200)  # 材料名称列
        self.result_table.horizontalHeader().setStretchLastSection(True)  # 让最后一列拉伸填满
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.result_table)
        
        # 配方分解树
        layout.addWidget(QLabel("配方分解树:"))
        if FLUENT_AVAILABLE:
            self.recipe_tree = TreeWidget()
        else:
            self.recipe_tree = QTreeWidget()
        
        self.recipe_tree.setHeaderLabels(["物品名称", "数量", "类型"])
        self.recipe_tree.setColumnWidth(0, 200)
        self.recipe_tree.setColumnWidth(1, 80)
        self.recipe_tree.setColumnWidth(2, 100)
        layout.addWidget(self.recipe_tree)
        
        return widget
    
    def create_recipe_management_page(self):
        """创建配方管理页面"""
        self.recipe_page = QWidget()
        self.recipe_page.setObjectName("recipe_page")
        layout = QVBoxLayout(self.recipe_page)
        layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        layout.setSpacing(5)  # 减少间距
        
        # 顶部操作菜单 - 设置固定高度
        menu_widget = self.create_recipe_menu_widget()
        menu_widget.setMaximumHeight(80)  # 限制操作菜单的最大高度
        layout.addWidget(menu_widget)
        
        # 主要内容区域
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：配方列表
        left_widget = self.create_recipe_list_widget()
        
        # 右侧：配方详情
        right_widget = self.create_recipe_detail_widget()
        
        content_splitter.addWidget(left_widget)
        content_splitter.addWidget(right_widget)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(content_splitter)
    
    def create_recipe_menu_widget(self):
        """创建配方操作菜单组件"""
        if FLUENT_AVAILABLE:
            # 使用普通的CardWidget代替HeaderCardWidget
            widget = CardWidget()
            # 添加标题
            title_label = QLabel("配方操作")
            title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
            
            # 创建内容布局
            content_layout = QVBoxLayout(widget)
            content_layout.setContentsMargins(10, 10, 10, 5)  # 减少边距
            content_layout.setSpacing(5)  # 减少间距
            content_layout.addWidget(title_label)
            
            # 创建按钮布局
            button_widget = QWidget()
            layout = QHBoxLayout(button_widget)
            layout.setContentsMargins(0, 5, 0, 0)  # 减少上边距
            layout.setSpacing(10)  # 设置按钮之间的间距
            content_layout.addWidget(button_widget)
        else:
            widget = QGroupBox("配方操作")
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
            layout.setSpacing(10)  # 设置按钮之间的间距
        
        # 添加配方按钮
        if FLUENT_AVAILABLE:
            self.add_recipe_btn = PrimaryPushButton("添加配方")
        else:
            self.add_recipe_btn = QPushButton("添加配方")
        self.add_recipe_btn.clicked.connect(self.add_new_recipe)
        self.add_recipe_btn.setFixedWidth(100)  # 设置固定宽度
        layout.addWidget(self.add_recipe_btn)
        
        # 删除配方按钮
        if FLUENT_AVAILABLE:
            self.delete_recipe_btn = PushButton("删除配方")
        else:
            self.delete_recipe_btn = QPushButton("删除配方")
        self.delete_recipe_btn.clicked.connect(self.on_delete_recipe_clicked)
        self.delete_recipe_btn.setFixedWidth(100)  # 设置固定宽度
        layout.addWidget(self.delete_recipe_btn)
        
        # 导入配方按钮
        if FLUENT_AVAILABLE:
            self.import_recipe_btn = PushButton("导入配方")
        else:
            self.import_recipe_btn = QPushButton("导入配方")
        self.import_recipe_btn.clicked.connect(self.on_import_recipe_clicked)
        self.import_recipe_btn.setFixedWidth(100)  # 设置固定宽度
        layout.addWidget(self.import_recipe_btn)
        
        # 导出配方按钮
        if FLUENT_AVAILABLE:
            self.export_recipe_btn = PushButton("导出配方")
        else:
            self.export_recipe_btn = QPushButton("导出配方")
        self.export_recipe_btn.clicked.connect(self.on_export_recipe_clicked)
        self.export_recipe_btn.setFixedWidth(100)  # 设置固定宽度
        layout.addWidget(self.export_recipe_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_recipe_list_widget(self):
        """创建配方列表组件"""
        if FLUENT_AVAILABLE:
            widget = SimpleCardWidget()
        else:
            widget = QGroupBox("配方管理")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        layout.setSpacing(5)  # 减少间距
        
        # 搜索和过滤
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        if FLUENT_AVAILABLE:
            self.recipe_search_edit = LineEdit()
        else:
            self.recipe_search_edit = QLineEdit()
        self.recipe_search_edit.setPlaceholderText("输入配方名称...")
        self.recipe_search_edit.textChanged.connect(self.filter_recipe_list)
        search_layout.addWidget(self.recipe_search_edit)
        
        search_layout.addWidget(QLabel("类型:"))
        if FLUENT_AVAILABLE:
            self.recipe_filter_combo = ComboBox()
        else:
            self.recipe_filter_combo = QComboBox()
        self.recipe_filter_combo.addItems(["全部", "半成品", "成品"])
        self.recipe_filter_combo.currentTextChanged.connect(self.filter_recipe_list)
        search_layout.addWidget(self.recipe_filter_combo)
        
        if FLUENT_AVAILABLE:
            refresh_button = PushButton("刷新")
        else:
            refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_recipe_list)
        search_layout.addWidget(refresh_button)
        
        layout.addLayout(search_layout)
        
        # 配方列表表格
        if FLUENT_AVAILABLE:
            self.recipe_list_table = TableWidget()
        else:
            self.recipe_list_table = QTableWidget()
        
        self.recipe_list_table.setColumnCount(4)
        self.recipe_list_table.setHorizontalHeaderLabels(["选择", "名称", "类型", "产出数量"])
        
        # 设置自定义表头到第一列
        self.recipe_list_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.recipe_list_table.setHorizontalHeaderItem(0, QTableWidgetItem(""))
        self.recipe_list_table.horizontalHeader().setDefaultSectionSize(60)
        
        # 设置列宽
        self.recipe_list_table.setColumnWidth(0, 60)   # 选择列（减小宽度，只需容纳复选框或序号）
        self.recipe_list_table.setColumnWidth(1, 200)  # 名称列
        self.recipe_list_table.setColumnWidth(2, 80)   # 类型列
        self.recipe_list_table.setColumnWidth(3, 100)  # 产出数量列
        
        # 设置表格属性
        self.recipe_list_table.horizontalHeader().setStretchLastSection(True)
        self.recipe_list_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.recipe_list_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recipe_list_table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 支持多选
        self.recipe_list_table.setAlternatingRowColors(True)  # 交替行颜色
        self.recipe_list_table.verticalHeader().setVisible(False)  # 隐藏垂直表头
        
        # 添加点击事件
        self.recipe_list_table.itemClicked.connect(self.on_recipe_selected)
        
        layout.addWidget(self.recipe_list_table)
        
        return widget
    
    def create_recipe_detail_widget(self):
        """创建配方详情组件"""
        if FLUENT_AVAILABLE:
            widget = SimpleCardWidget()
        else:
            widget = QGroupBox("配方详情")
        
        layout = QVBoxLayout(widget)
        
        # 配方详情显示和编辑按钮的水平布局
        detail_layout = QHBoxLayout()
        
        # 配方详情显示
        self.recipe_detail_label = QLabel("请选择一个配方查看详情")
        self.recipe_detail_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        detail_layout.addWidget(self.recipe_detail_label)
        
        # 编辑按钮
        if FLUENT_AVAILABLE:
            self.edit_recipe_button = PushButton("编辑配方")
        else:
            self.edit_recipe_button = QPushButton("编辑配方")
        self.edit_recipe_button.setEnabled(False)  # 初始状态禁用
        self.edit_recipe_button.clicked.connect(self.edit_selected_recipe)
        detail_layout.addWidget(self.edit_recipe_button)
        
        layout.addLayout(detail_layout)
        
        # 配方分解树
        layout.addWidget(QLabel("配方分解:"))
        if FLUENT_AVAILABLE:
            self.recipe_detail_tree = TreeWidget()
        else:
            self.recipe_detail_tree = QTreeWidget()
        
        self.recipe_detail_tree.setHeaderLabels(["物品名称", "数量", "类型"])
        self.recipe_detail_tree.setColumnWidth(0, 200)
        self.recipe_detail_tree.setColumnWidth(1, 80)
        self.recipe_detail_tree.setColumnWidth(2, 100)
        layout.addWidget(self.recipe_detail_tree)
        
        return widget
    

    
    def on_page_changed(self, index):
        """页面切换事件处理器"""
        try:
            # 根据不同的界面类型获取当前页面
            if FLUENT_AVAILABLE:
                # Fluent界面：索引1是配方管理页面
                if index == 1:
                    self.refresh_recipe_list()
                elif index == 0:
                    self.refresh_item_list()
            else:
                # 标准界面：索引1是配方管理页面
                if index == 1:
                    self.refresh_recipe_list()
                elif index == 0:
                    self.refresh_item_list()
        except Exception as e:
            self.show_message(f"页面切换处理失败: {str(e)}", "error")
    
    def load_data(self):
        """加载数据"""
        # 检查并添加示例数据
        self.ensure_sample_data()
        self.refresh_item_list()
        self.refresh_recipe_list()
    
    def ensure_sample_data(self):
        """确保有示例数据"""
        # 检查是否已有数据
        base_materials = self.db_manager.get_base_materials()
        if len(base_materials) == 0:
            # 添加示例原材料
            self.db_manager.add_base_material("白钢矿", "基础矿物材料")
            self.db_manager.add_base_material("胡桃", "基础植物材料")
            self.db_manager.add_base_material("橡木长弓", "基础木材材料")
            self.db_manager.add_base_material("水晶", "基础水晶材料")
            self.db_manager.add_base_material("棉花", "基础纤维材料")
            
            # 添加示例半成品
            material_id1 = self.db_manager.add_material("白钢锭", 3, "冶炼后的白钢")
            material_id2 = self.db_manager.add_material("胡桃油", 1, "提炼的胡桃油")
            material_id3 = self.db_manager.add_material("橡木板", 6, "加工的橡木板")
            material_id4 = self.db_manager.add_material("棉布", 2, "编织的棉布")
            
            # 添加示例成品
            product_id1 = self.db_manager.add_product("白钢剑", 1, "高级武器")
            product_id2 = self.db_manager.add_product("煎饼", 3, "美味食物")
            
            # 添加配方需求
            # 白钢锭配方：需要3个白钢矿
            base_material_ids = {item['name']: item['id'] for item in self.db_manager.get_base_materials()}
            self.db_manager.add_recipe_requirement('material', material_id1, 'base', base_material_ids['白钢矿'], 3.0)
            
            # 胡桃油配方：需要3个胡桃
            self.db_manager.add_recipe_requirement('material', material_id2, 'base', base_material_ids['胡桃'], 3.0)
            
            # 橡木板配方：需要1个橡木长弓
            self.db_manager.add_recipe_requirement('material', material_id3, 'base', base_material_ids['橡木长弓'], 1.0)
            
            # 棉布配方：需要2个棉花
            self.db_manager.add_recipe_requirement('material', material_id4, 'base', base_material_ids['棉花'], 2.0)
            
            # 白钢剑配方：需要1个白钢锭 + 1个橡木板
            self.db_manager.add_recipe_requirement('product', product_id1, 'material', material_id1, 1.0)
            self.db_manager.add_recipe_requirement('product', product_id1, 'material', material_id3, 1.0)
            
            # 煎饼配方：需要1个胡桃油 + 1个棉布
            self.db_manager.add_recipe_requirement('product', product_id2, 'material', material_id2, 1.0)
            self.db_manager.add_recipe_requirement('product', product_id2, 'material', material_id4, 1.0)
    
    def refresh_item_list(self):
        """刷新物品列表"""
        current_type = self.type_combo.currentText()
        search_text = self.search_edit.text().strip()
        
        if current_type == "成品":
            items = self.db_manager.get_products()
        else:
            items = self.db_manager.get_materials()
        
        # 过滤搜索结果
        if search_text:
            items = [item for item in items if search_text.lower() in item['name'].lower()]
        
        # 更新表格
        self.item_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.item_table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.item_table.setItem(i, 1, QTableWidgetItem(self.format_number(item.get('output_quantity', 1))))
            
            # 添加查看按钮
            view_button = QPushButton("查看配方")
            if current_type == "成品":
                item_type = 'product'
            else:
                item_type = 'material'
            view_button.clicked.connect(lambda checked, t=item_type, item_id=item['id']: self.view_recipe(t, item_id))
            self.item_table.setCellWidget(i, 2, view_button)
    
    def refresh_recipe_list(self):
        """刷新配方列表"""
        try:
            # 清空表格
            self.recipe_list_table.setRowCount(0)
            
            # 获取所有半成品和成品
            materials = self.db_manager.get_materials()
            products = self.db_manager.get_products()
            
            # 合并数据
            all_items = []
            for material in materials:
                all_items.append({
                    'id': material['id'],
                    'name': material['name'],
                    'type': '半成品',
                    'output_quantity': material['output_quantity'],
                    'item_type': 'material'
                })
            
            for product in products:
                all_items.append({
                    'id': product['id'],
                    'name': product['name'],
                    'type': '成品',
                    'output_quantity': product['output_quantity'],
                    'item_type': 'product'
                })
            
            # 填充表格
            self.recipe_list_table.setRowCount(len(all_items))
            
            # 设置表头文本
            self.recipe_list_table.setHorizontalHeaderItem(0, QTableWidgetItem(""))
            
            for row, item in enumerate(all_items):
                # 选择列显示序号（从1开始）
                index_item = QTableWidgetItem(str(row + 1))
                index_item.setTextAlignment(Qt.AlignCenter)
                self.recipe_list_table.setItem(row, 0, index_item)
                
                # 名称
                name_item = QTableWidgetItem(item['name'])
                self.recipe_list_table.setItem(row, 1, name_item)
                
                # 类型
                type_item = QTableWidgetItem(item['type'])
                self.recipe_list_table.setItem(row, 2, type_item)
                
                # 产出数量
                quantity_item = QTableWidgetItem(self.format_number(item['output_quantity']))
                self.recipe_list_table.setItem(row, 3, quantity_item)
                
                # 存储物品信息到表格项中
                name_item.setData(Qt.UserRole, {'type': item['item_type'], 'id': item['id']})
            
            # 确保表格可见并应用过滤器
            self.recipe_list_table.setVisible(True)
            self.filter_recipe_list()
                
        except Exception as e:
            self.show_message(f"刷新配方列表失败: {str(e)}", "error")
    
    def on_recipe_selected(self, item):
        """配方选择事件处理"""
        try:
            if not item:
                return
            
            # 获取选中行的数据
            row = item.row()
            name_item = self.recipe_list_table.item(row, 1)  # 名称列现在是第1列
            if not name_item:
                return
            
            item_data = name_item.data(Qt.UserRole)
            if not item_data:
                return
            
            item_type = item_data['type']
            item_id = item_data['id']
            
            # 获取物品信息
            if item_type == 'material':
                item_info = self.db_manager.get_material_by_id(item_id)
                recipe_type = 'material'
            else:
                item_info = self.db_manager.get_product_by_id(item_id)
                recipe_type = 'product'
            
            if not item_info:
                self.recipe_detail_label.setText("物品不存在")
                self.recipe_detail_tree.clear()
                return
            
            # 更新详情标签
            type_text = '半成品' if item_type == 'material' else '成品'
            detail_text = f"配方详情: {item_info['name']} ({type_text}) - 产出数量: {self.format_number(item_info['output_quantity'])}"
            self.recipe_detail_label.setText(detail_text)
            
            # 构建配方树
            self.recipe_detail_tree.clear()
            tree_data = self.calculator.get_recipe_tree(item_type, item_id, 1)
            if tree_data:
                tree_item = self.create_tree_item(tree_data)
                self.recipe_detail_tree.addTopLevelItem(tree_item)
                self.recipe_detail_tree.expandAll()
            
            # 存储当前选中的配方信息
            self.current_selected_recipe = {'type': item_type, 'id': item_id}
            
            # 启用编辑按钮
            self.edit_recipe_button.setEnabled(True)
            
        except Exception as e:
            self.show_message(f"显示配方详情失败: {str(e)}", "error")
    
    def add_new_recipe(self):
        """添加新配方 - 分层级添加"""
        try:
            dialog = RecipeAddDialog(self, self.db_manager)
            if dialog.exec() == QDialog.Accepted:
                self.refresh_recipe_list()
                self.refresh_item_list()
                self.show_message("配方添加成功", "success")
        except Exception as e:
            self.show_message(f"添加配方失败: {str(e)}", "error")
    
    def edit_selected_recipe(self):
        """编辑选中的配方"""
        if not hasattr(self, 'current_selected_recipe') or not self.current_selected_recipe:
            self.show_message("请先选择一个配方", "warning")
            return
        
        try:
            item_type = self.current_selected_recipe['type']
            item_id = self.current_selected_recipe['id']
            
            # 获取物品信息
            if item_type == 'material':
                item_info = self.db_manager.get_material_by_id(item_id)
            else:
                item_info = self.db_manager.get_product_by_id(item_id)
            
            if not item_info:
                self.show_message("配方不存在", "error")
                return
            
            # 打开编辑对话框
            dialog = RecipeAddDialog(self, self.db_manager, edit_mode=True, 
                                   item_type=item_type, item_id=item_id)
            if dialog.exec() == QDialog.Accepted:
                self.refresh_recipe_list()
                self.refresh_item_list()
                # 重新选择当前配方以更新详情显示
                self.on_recipe_selected(self.recipe_list_table.currentItem())
                self.show_message("配方编辑成功", "success")
                
        except Exception as e:
            self.show_message(f"编辑配方失败: {str(e)}", "error")
    
    def delete_selected_recipe(self):
        """删除选中的配方"""
        if not hasattr(self, 'current_selected_recipe') or not self.current_selected_recipe:
            self.show_message("请先选择一个配方", "warning")
            return
        
        try:
            item_type = self.current_selected_recipe['type']
            item_id = self.current_selected_recipe['id']
            
            # 获取物品名称用于确认
            if item_type == 'material':
                item_info = self.db_manager.get_material_by_id(item_id)
            else:
                item_info = self.db_manager.get_product_by_id(item_id)
            
            if not item_info:
                self.show_message("配方不存在", "error")
                return
            
            # 确认删除
            reply = QMessageBox.question(
                self, "确认删除", 
                f"确定要删除配方 '{item_info['name']}' 吗？\n此操作不可撤销。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.delete_recipe(item_type, item_id)
                
        except Exception as e:
            self.show_message(f"删除配方失败: {str(e)}", "error")
    
    def on_delete_recipe_clicked(self):
        """删除配方按钮点击事件"""
        # 获取选中的行
        selected_rows = []
        for row in range(self.recipe_list_table.rowCount()):
            if self.recipe_list_table.item(row, 0) and self.recipe_list_table.item(row, 0).isSelected():
                selected_rows.append(row)
        
        # 如果没有选中行，检查当前行
        if not selected_rows:
            current_row = self.recipe_list_table.currentRow()
            if current_row >= 0:
                selected_rows = [current_row]
        
        if not selected_rows:
            self.show_message("请选择要删除的配方", "warning")
            return
        
        # 收集要删除的配方信息
        recipes_to_delete = []
        for row in selected_rows:
            name_item = self.recipe_list_table.item(row, 1)
            type_item = self.recipe_list_table.item(row, 2)
            if name_item and type_item:
                recipe_name = name_item.text()
                recipe_type = "material" if type_item.text() == "半成品" else "product"
                recipes_to_delete.append((recipe_name, recipe_type))
        
        if not recipes_to_delete:
            self.show_message("无法获取配方信息", "error")
            return
        
        # 二次确认删除
        recipe_names = [name for name, _ in recipes_to_delete]
        if len(recipes_to_delete) == 1:
            message = f"确定要删除配方 '{recipe_names[0]}' 吗？"
        else:
            message = f"确定要删除以下 {len(recipes_to_delete)} 个配方吗？\n\n{', '.join(recipe_names[:5])}{'...' if len(recipe_names) > 5 else ''}\n\n此操作不可撤销。"
        
        reply = QMessageBox.question(
            self, "确认删除", message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                deleted_count = 0
                for recipe_name, recipe_type in recipes_to_delete:
                    # 获取配方ID
                    if recipe_type == "material":
                        item = self.db_manager.get_material_by_name(recipe_name)
                    else:
                        item = self.db_manager.get_product_by_name(recipe_name)
                    
                    if item:
                        if recipe_type == "material":
                            self.db_manager.delete_material(item['id'])
                        else:
                            self.db_manager.delete_product(item['id'])
                        deleted_count += 1
                
                self.show_message(f"成功删除 {deleted_count} 个配方", "success")
                self.refresh_recipe_list()
                self.refresh_item_list()
                
            except Exception as e:
                self.show_message(f"删除配方失败: {str(e)}", "error")
    

    
    def on_search_changed(self):
        """搜索文本改变"""
        self.refresh_item_list()
    
    def on_type_changed(self):
        """类型改变"""
        self.refresh_item_list()
    
    def add_selected_item(self):
        """添加选中的物品到计算列表"""
        current_row = self.item_table.currentRow()
        if current_row < 0:
            self.show_message("请先选择一个物品", "warning")
            return
        
        item_name = self.item_table.item(current_row, 0).text()
        current_type = self.type_combo.currentText()
        
        # 获取物品信息
        if current_type == "成品":
            item = self.db_manager.get_product_by_name(item_name)
            item_type = 'product'
        else:
            item = self.db_manager.get_material_by_name(item_name)
            item_type = 'material'
        
        if not item:
            self.show_message("物品不存在", "error")
            return
        
        # 检查是否已添加
        for selected_item in self.selected_items:
            if selected_item['id'] == item['id'] and selected_item['type'] == item_type:
                self.show_message("该物品已在计算列表中", "warning")
                return
        
        # 添加到列表
        self.selected_items.append({
            'id': item['id'],
            'name': item['name'],
            'type': item_type,
            'quantity': 1
        })
        
        self.refresh_selected_items()
    
    def refresh_selected_items(self):
        """刷新已选择物品列表"""
        self.selected_table.setRowCount(len(self.selected_items))
        for i, item in enumerate(self.selected_items):
            self.selected_table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.selected_table.setItem(i, 1, QTableWidgetItem('成品' if item['type'] == 'product' else '半成品'))
            
            # 数量输入框
            quantity_spin = QSpinBox()
            quantity_spin.setMinimum(1)
            quantity_spin.setValue(item['quantity'])
            quantity_spin.valueChanged.connect(lambda value, idx=i: self.update_item_quantity(idx, value))
            self.selected_table.setCellWidget(i, 2, quantity_spin)
            
            # 删除按钮
            remove_button = QPushButton("移除")
            remove_button.clicked.connect(lambda checked, idx=i: self.remove_selected_item(idx))
            self.selected_table.setCellWidget(i, 3, remove_button)
    
    def update_item_quantity(self, index: int, quantity: int):
        """更新物品数量"""
        if 0 <= index < len(self.selected_items):
            self.selected_items[index]['quantity'] = quantity
    
    def remove_selected_item(self, index: int):
        """移除选中的物品"""
        if 0 <= index < len(self.selected_items):
            self.selected_items.pop(index)
            self.refresh_selected_items()
    
    def calculate_requirements(self):
        """计算材料需求"""
        if not self.selected_items:
            self.show_message("请先添加要计算的物品", "warning")
            return
        
        # 使用工作线程进行计算
        self.calculation_worker = CalculationWorker(self.calculator, self.selected_items)
        self.calculation_worker.finished.connect(self.on_calculation_finished)
        self.calculation_worker.error.connect(self.on_calculation_error)
        self.calculation_worker.start()
        
        self.calculate_button.setEnabled(False)
        self.calculate_button.setText("计算中...")
    
    def on_calculation_finished(self, result: Dict[str, Any]):
        """计算完成"""
        self.calculate_button.setEnabled(True)
        self.calculate_button.setText("计算材料需求")
        
        # 显示结果
        requirements = result['requirements']
        self.result_table.setRowCount(len(requirements))
        
        for i, req in enumerate(requirements):
            self.result_table.setItem(i, 0, QTableWidgetItem(req['name']))
            self.result_table.setItem(i, 1, QTableWidgetItem(self.format_number(req['quantity'])))
        
        # 构建配方树
        self.build_recipe_tree()
        
        self.show_message(f"计算完成，需要 {len(requirements)} 种基础材料", "success")
    
    def on_calculation_error(self, error: str):
        """计算错误"""
        self.calculate_button.setEnabled(True)
        self.calculate_button.setText("计算材料需求")
        self.show_message(f"计算失败: {error}", "error")
    
    def build_recipe_tree(self):
        """构建配方树"""
        self.recipe_tree.clear()
        
        for item in self.selected_items:
            tree_data = self.calculator.get_recipe_tree(item['type'], item['id'], item['quantity'])
            if tree_data:
                tree_item = self.create_tree_item(tree_data)
                self.recipe_tree.addTopLevelItem(tree_item)
        
        self.recipe_tree.expandAll()
    
    def create_tree_item(self, data: Dict[str, Any]) -> QTreeWidgetItem:
        """创建树形项"""
        item_name = data.get('name', f"ID: {data['id']}")
        item_type = data['type']
        quantity = data['quantity']
        
        item_type_map = {
            'base': '原材料',
            'material': '半成品', 
            'product': '成品'
        }
        type_text = item_type_map.get(item_type, item_type)
        
        tree_item = QTreeWidgetItem([item_name, self.format_number(quantity), type_text])
        
        # 递归添加子项
        for child_data in data.get('children', []):
            child_item = self.create_tree_item(child_data)
            tree_item.addChild(child_item)
        
        return tree_item
    
    def view_recipe(self, item_type: str, item_id: int):
        """查看配方详情"""
        tree_data = self.calculator.get_recipe_tree(item_type, item_id, 1)
        if tree_data:
            # 创建美观的配方详情对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("配方详情")
            dialog.setMinimumSize(500, 400)
            dialog.resize(600, 500)
            
            layout = QVBoxLayout(dialog)
            
            # 标题
            item_name = tree_data.get('name', '未知物品')
            title_label = QLabel(f"配方详情: {item_name}")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(title_label)
            
            # 配方树显示
            tree_widget = QTreeWidget()
            tree_widget.setHeaderLabels(["物品名称", "数量", "类型"])
            tree_widget.setColumnWidth(0, 250)  # 增加物品名称列宽
            tree_widget.setColumnWidth(1, 100)  # 增加数量列宽
            tree_widget.horizontalHeader().setStretchLastSection(True)  # 让最后一列自动拉伸
            tree_widget.setAlternatingRowColors(True)  # 交替行颜色
            tree_widget.setRootIsDecorated(True)  # 显示树形结构线条
            tree_widget.setIndentation(20)  # 设置缩进
            
            # 添加配方树数据
            root_item = self.create_tree_item_for_dialog(tree_data)
            tree_widget.addTopLevelItem(root_item)
            tree_widget.expandAll()
            
            layout.addWidget(tree_widget)
            
            # 按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            ok_button = QPushButton("确定")
            ok_button.clicked.connect(dialog.accept)
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            
            dialog.exec()
        else:
            self.show_message("该物品没有配方信息", "warning")
    
    def calculate_requirements(self):
        """计算材料需求"""
        if not self.selected_items:
            self.show_message("请先添加要计算的物品", "warning")
            return
        
        # 使用工作线程进行计算
        self.calculation_worker = CalculationWorker(self.calculator, self.selected_items)
        self.calculation_worker.finished.connect(self.on_calculation_finished)
        self.calculation_worker.error.connect(self.on_calculation_error)
        self.calculation_worker.start()
        
        self.calculate_button.setEnabled(False)
        self.calculate_button.setText("计算中...")
    
    def show_calculation_result(self, item_name: str, quantity: int, requirements: Dict[str, int]):
        """在新窗口显示计算结果"""
        # 创建结果显示对话框
        result_dialog = QMessageBox(self)
        result_dialog.setWindowTitle("计算结果")
        result_dialog.setIcon(QMessageBox.Information)
        
        # 格式化结果文本
        result_text = f"制作 {item_name} x{self.format_number(quantity)} 需要的基础材料:\n\n"
        for material_name, needed_quantity in requirements.items():
            result_text += f"{material_name}: {self.format_number(needed_quantity)}\n"
        
        result_dialog.setText(result_text)
        result_dialog.exec()
    
    def create_tree_item_for_dialog(self, data: Dict[str, Any]) -> QTreeWidgetItem:
        """为对话框创建树形项"""
        item_name = data.get('name', f"ID: {data['id']}")
        quantity = self.format_number(data['quantity'])
        item_type_map = {
            'base': '原材料',
            'material': '半成品', 
            'product': '成品'
        }
        item_type = item_type_map.get(data['type'], data['type'])
        
        tree_item = QTreeWidgetItem([item_name, quantity, item_type])
        
        # 根据类型设置不同的颜色
        if data['type'] == 'base':
            tree_item.setForeground(0, QColor(34, 139, 34))  # 绿色 - 原材料
            tree_item.setForeground(2, QColor(34, 139, 34))
        elif data['type'] == 'material':
            tree_item.setForeground(0, QColor(255, 140, 0))  # 橙色 - 半成品
            tree_item.setForeground(2, QColor(255, 140, 0))
        else:  # product
            tree_item.setForeground(0, QColor(30, 144, 255))  # 蓝色 - 成品
            tree_item.setForeground(2, QColor(30, 144, 255))
        
        # 数量列居中对齐
        tree_item.setTextAlignment(1, Qt.AlignCenter)
        
        # 递归添加子项
        for child_data in data.get('children', []):
            child_item = self.create_tree_item_for_dialog(child_data)
            tree_item.addChild(child_item)
        
        return tree_item
    
    def format_recipe_tree(self, data: Dict[str, Any], indent: int = 0) -> str:
        """格式化配方树为文本"""
        prefix = "  " * indent
        item_name = data.get('name', f"ID: {data['id']}")
        quantity = data['quantity']
        item_type_map = {
            'base': '原材料',
            'material': '半成品', 
            'product': '成品'
        }
        item_type = item_type_map.get(data['type'], data['type'])
        
        result = f"{prefix}{item_name} x{self.format_number(quantity)} ({item_type})\n"
        
        for child in data.get('children', []):
            result += self.format_recipe_tree(child, indent + 1)
        
        return result
    
    def add_recipe(self):
        """添加配方"""
        name = self.recipe_name_edit.text().strip()
        if not name:
            self.show_message("请输入物品名称", "warning")
            return
        
        recipe_type = self.recipe_type_combo.currentText()
        output_quantity = self.recipe_output_spin.value()
        requirements = self.current_requirements.copy()  # 使用当前需求列表
        
        try:
            # 添加物品
            if recipe_type == "半成品":
                item_id = self.db_manager.add_material(name, output_quantity)
                item_type = 'material'
            else:
                item_id = self.db_manager.add_product(name, output_quantity)
                item_type = 'product'
            
            # 添加配方需求
            for req in requirements:
                req_type = req['type']
                req_name = req['name']
                req_quantity = req['quantity']
                
                # 查找材料ID
                if req_type == 'base':
                    material = self.db_manager.get_base_material_by_name(req_name)
                    if material:
                        self.db_manager.add_recipe_requirement(item_type, item_id, 'base', material['id'], req_quantity)
                elif req_type == 'material':
                    material = self.db_manager.get_material_by_name(req_name)
                    if material:
                        self.db_manager.add_recipe_requirement(item_type, item_id, 'material', material['id'], req_quantity)
            
            self.show_message("配方添加成功", "success")
            self.clear_recipe_form()
            self.refresh_recipe_list()
            self.refresh_item_list()
            
        except Exception as e:
            self.show_message(f"添加配方失败: {str(e)}", "error")
    
    def delete_recipe(self, item_type: str, item_id: int):
        """删除配方"""
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个配方吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if item_type == 'material':
                    self.db_manager.delete_material(item_id)
                else:
                    self.db_manager.delete_product(item_id)
                
                self.show_message("配方删除成功", "success")
                self.refresh_recipe_list()
                self.refresh_item_list()
                
            except Exception as e:
                self.show_message(f"删除配方失败: {str(e)}", "error")
    
    def browse_csv_file(self):
        """浏览CSV文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV文件 (*.csv)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
    
    def download_template(self):
        """下载CSV模板"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存模板文件", "配方模板.csv", "CSV文件 (*.csv)"
        )
        if file_path:
            if self.csv_importer.export_template(file_path):
                self.show_message("模板下载成功", "success")
            else:
                self.show_message("模板下载失败", "error")
    
    def import_csv_data(self):
        """导入CSV数据"""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            self.show_message("请选择CSV文件", "warning")
            return
        
        if not os.path.exists(file_path):
            self.show_message("文件不存在", "error")
            return
        
        # 使用工作线程导入
        self.import_worker = ImportWorker(self.csv_importer, file_path)
        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.error.connect(self.on_import_error)
        self.import_worker.progress.connect(self.on_import_progress)
        self.import_worker.start()
        
        self.import_progress.setVisible(True)
        self.import_progress.setRange(0, 0)  # 不确定进度
    
    def on_import_progress(self, message: str):
        """导入进度更新"""
        self.statusBar().showMessage(message)
    
    def on_import_finished(self, result: Dict[str, Any]):
        """导入完成"""
        self.import_progress.setVisible(False)
        self.statusBar().clearMessage()
        
        if result['success']:
            counts = result['imported_counts']
            message = f"导入成功！原材料: {counts['base_materials']}, 半成品: {counts['materials']}, 成品: {counts['products']}"
            self.show_message(message, "success")
        else:
            self.show_message(f"导入失败: {result['message']}", "error")
        
        self.refresh_recipe_list()
        self.refresh_item_list()
    
    def on_import_error(self, error: str):
        """导入错误"""
        self.import_progress.setVisible(False)
        self.statusBar().clearMessage()
        self.show_message(f"导入失败: {error}", "error")
    
    def export_csv_data(self):
        """导出CSV数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存CSV文件", "配方数据.csv", "CSV文件 (*.csv)"
        )
        if file_path:
            try:
                self.csv_importer.export_to_csv(file_path)
                self.show_message("数据导出成功", "success")
            except Exception as e:
                self.show_message(f"导出失败: {str(e)}", "error")
    
    def migrate_json_data(self):
        """迁移JSON数据"""
        reply = QMessageBox.question(
            self, "确认迁移", "确定要从JSON文件迁移数据到数据库吗？这将覆盖现有数据。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                migrator = DataMigrator(self.db_manager)
                result = migrator.migrate_all()
                
                if result['success']:
                    counts = result['migrated_counts']
                    message = f"迁移成功！原材料: {counts['base_materials']}, 半成品: {counts['materials']}, 成品: {counts['products']}"
                    self.show_message(message, "success")
                else:
                    self.show_message(f"迁移失败: {result['message']}", "error")
                
                self.refresh_recipe_list()
                self.refresh_item_list()
                
            except Exception as e:
                self.show_message(f"迁移失败: {str(e)}", "error")
    
    def on_item_double_clicked(self, item):
        """物品双击事件"""
        self.add_selected_item()
    
    def show_message(self, message: str, msg_type: str = "info"):
        """显示消息"""
        if FLUENT_AVAILABLE:
            if msg_type == "success":
                InfoBar.success(
                    title="成功",
                    content=message,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            elif msg_type == "warning":
                InfoBar.warning(
                    title="警告",
                    content=message,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            elif msg_type == "error":
                InfoBar.error(
                    title="错误",
                    content=message,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )
            else:
                InfoBar.info(
                    title="信息",
                    content=message,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        else:
            # 使用标准消息框
            if msg_type == "error":
                QMessageBox.critical(self, "错误", message)
            elif msg_type == "warning":
                QMessageBox.warning(self, "警告", message)
            else:
                QMessageBox.information(self, "信息", message)
    
    def filter_recipe_list(self):
        """过滤配方列表"""
        search_text = self.recipe_search_edit.text().strip().lower()
        filter_type = self.recipe_filter_combo.currentText()
        
        # 获取所有行
        visible_row_count = 0
        for row in range(self.recipe_list_table.rowCount()):
            show_row = True
            
            # 检查搜索文本
            if search_text:
                name_item = self.recipe_list_table.item(row, 1)  # 名称列现在是第1列
                if name_item and search_text not in name_item.text().lower():
                    show_row = False
            
            # 检查类型过滤
            if filter_type != "全部":
                type_item = self.recipe_list_table.item(row, 2)  # 类型列现在是第2列
                if type_item and type_item.text() != filter_type:
                    show_row = False
            
            self.recipe_list_table.setRowHidden(row, not show_row)
            
            # 如果行可见，更新序号为从1开始的连续数字
            if show_row:
                visible_row_count += 1
                index_item = QTableWidgetItem(str(visible_row_count))
                index_item.setTextAlignment(Qt.AlignCenter)
                self.recipe_list_table.setItem(row, 0, index_item)
    
    def clear_recipe_form(self):
        """清空配方表单"""
        self.recipe_name_edit.clear()
        self.recipe_type_combo.setCurrentIndex(0)
        self.recipe_output_spin.setValue(1)
        self.req_name_edit.clear()
        self.req_quantity_spin.setValue(1)
        self.current_requirements.clear()
        self.requirements_table.setRowCount(0)
        self.suggestion_list.setVisible(False)
        self.show_message("表单已清空", "info")
    
    def on_requirement_name_changed(self):
        """需求名称输入改变时的处理"""
        text = self.req_name_edit.text().strip()
        if len(text) >= 1:  # 输入至少1个字符时开始搜索
            self.show_suggestions(text)
        else:
            self.suggestion_list.setVisible(False)
    
    def show_suggestions(self, keyword: str):
        """显示搜索建议"""
        try:
            # 根据当前选择的类型搜索
            req_type = self.req_type_combo.currentText()
            suggestions = []
            
            if req_type == "原材料":
                base_materials = self.db_manager.get_base_materials()
                suggestions = [item for item in base_materials if keyword.lower() in item['name'].lower()]
            else:  # 半成品
                materials = self.db_manager.get_materials()
                suggestions = [item for item in materials if keyword.lower() in item['name'].lower()]
            
            # 更新建议列表
            self.suggestion_list.clear()
            if suggestions:
                for item in suggestions[:10]:  # 最多显示10个建议
                    self.suggestion_list.addItem(item['name'])
                self.suggestion_list.setVisible(True)
            else:
                self.suggestion_list.setVisible(False)
                
        except Exception as e:
            print(f"搜索建议时出错: {e}")
            self.suggestion_list.setVisible(False)
    
    def on_suggestion_selected(self, item):
        """选择建议项时的处理"""
        self.req_name_edit.setText(item.text())
        self.suggestion_list.setVisible(False)
    
    def add_requirement(self):
        """添加配方需求"""
        req_type = self.req_type_combo.currentText()
        req_name = self.req_name_edit.text().strip()
        req_quantity = self.req_quantity_spin.value()
        
        if not req_name:
            self.show_message("请输入物品名称", "warning")
            return
        
        # 验证物品是否存在
        item = None
        if req_type == "原材料":
            item = self.db_manager.get_base_material_by_name(req_name)
            item_type = "base"
        else:  # 半成品
            item = self.db_manager.get_material_by_name(req_name)
            item_type = "material"
        
        if not item:
            self.show_message(f"找不到名为 '{req_name}' 的{req_type}", "error")
            return
        
        # 检查是否已添加
        for req in self.current_requirements:
            if req['type'] == item_type and req['id'] == item['id']:
                self.show_message(f"'{req_name}' 已在需求列表中", "warning")
                return
        
        # 添加到需求列表
        requirement = {
            'type': item_type,
            'id': item['id'],
            'name': req_name,
            'quantity': req_quantity
        }
        self.current_requirements.append(requirement)
        
        # 更新表格显示
        self.refresh_requirements_table()
        
        # 清空输入
        self.req_name_edit.clear()
        self.req_quantity_spin.setValue(1)
        self.suggestion_list.setVisible(False)
    
    def refresh_requirements_table(self):
        """刷新需求表格"""
        self.requirements_table.setRowCount(len(self.current_requirements))
        
        for row, req in enumerate(self.current_requirements):
            # 类型
            type_text = "原材料" if req['type'] == "base" else "半成品"
            self.requirements_table.setItem(row, 0, QTableWidgetItem(type_text))
            
            # 名称
            self.requirements_table.setItem(row, 1, QTableWidgetItem(req['name']))
            
            # 数量
            self.requirements_table.setItem(row, 2, QTableWidgetItem(self.format_number(req['quantity'])))
            
            # 删除按钮
            delete_button = QPushButton("删除")
            delete_button.clicked.connect(lambda checked, idx=row: self.remove_requirement(idx))
            self.requirements_table.setCellWidget(row, 3, delete_button)
    
    def remove_requirement(self, index: int):
        """移除需求"""
        if 0 <= index < len(self.current_requirements):
            removed_req = self.current_requirements.pop(index)
            self.refresh_requirements_table()
            self.show_message(f"已移除需求: {removed_req['name']}", "info")
    
    def view_recipe(self, item_type: str, item_id: int):
        """查看配方详情"""
        try:
            # 获取物品信息
            if item_type == 'material':
                item = self.db_manager.get_material_by_id(item_id)
                recipe_type = 'material'
            else:
                item = self.db_manager.get_product_by_id(item_id)
                recipe_type = 'product'
            
            if not item:
                self.show_message("物品不存在", "error")
                return
            
            # 获取配方需求
            requirements = self.db_manager.get_recipe_requirements(recipe_type, item_id)
            
            # 构建详情信息
            details = f"配方详情\n\n"
            details += f"名称: {item['name']}\n"
            details += f"类型: {'半成品' if item_type == 'material' else '成品'}\n"
            details += f"产出数量: {self.format_number(item['output_quantity'])}\n\n"
            
            if requirements:
                details += "配方需求:\n"
                for req in requirements:
                    # 获取需求物品名称
                    if req['ingredient_type'] == 'base':
                        ingredient = self.db_manager.get_base_material_by_id(req['ingredient_id'])
                        type_name = "原材料"
                    else:
                        ingredient = self.db_manager.get_material_by_id(req['ingredient_id'])
                        type_name = "半成品"
                    
                    if ingredient:
                        details += f"  - {type_name}: {ingredient['name']} x{self.format_number(req['quantity'])}\n"
            else:
                details += "无配方需求\n"
            
            # 显示详情对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("配方详情")
            msg_box.setText(details)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            
        except Exception as e:
            self.show_message(f"查看配方失败: {str(e)}", "error")
    
    def on_import_recipe_clicked(self):
        """导入配方按钮点击事件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配方文件", "", "CSV文件 (*.csv)"
        )
        if file_path:
            try:
                # 检测CSV格式并选择合适的导入方法
                import csv
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames
                    
                    # 检查是否为新的三列格式
                    if '物品名称' in headers and '物品类型' in headers and '所需材料' in headers:
                        self.import_recipes_from_csv(file_path)
                    else:
                        # 使用旧格式导入
                        self.import_recipes_from_csv_with_dedup(file_path)
                        
            except Exception as e:
                self.show_message(f"导入配方失败: {str(e)}", "error")
    
    def on_export_recipe_clicked(self):
        """导出配方按钮点击事件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配方文件", "recipes.csv", "CSV文件 (*.csv)"
        )
        if file_path:
            try:
                # 检查文件是否被占用
                import os
                if os.path.exists(file_path):
                    try:
                        # 尝试以写入模式打开文件来检查是否被占用
                        with open(file_path, 'a') as test_file:
                            pass
                    except PermissionError:
                        self.show_message(f"文件被占用或权限不足，请关闭相关程序后重试: {file_path}", "error")
                        return
                
                self.export_recipes_to_csv(file_path)
            except PermissionError as e:
                self.show_message(f"权限错误: 请确保文件未被其他程序占用，或以管理员身份运行程序\n{str(e)}", "error")
            except Exception as e:
                self.show_message(f"导出配方失败: {str(e)}", "error")
    
    def import_recipes_from_csv_with_dedup(self, file_path: str):
        """从CSV文件导入配方（带去重机制）"""
        import csv
        
        imported_count = 0
        skipped_count = 0
        
        # 检测文件编码
        encoding = self._detect_file_encoding(file_path)
        print(f"检测到文件编码: {encoding}")
        
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    name = row['name'].strip()
                    recipe_type = row['type'].strip()
                    output_quantity = int(row.get('output_quantity', 1))
                    
                    # 检查是否已存在
                    existing_item = None
                    if recipe_type == "半成品":
                        existing_item = self.db_manager.get_material_by_name(name)
                    elif recipe_type == "成品":
                        existing_item = self.db_manager.get_product_by_name(name)
                    
                    if existing_item:
                        skipped_count += 1
                        continue
                    
                    # 添加新配方
                    if recipe_type == "半成品":
                        item_id = self.db_manager.add_material(name, output_quantity)
                        item_type = 'material'
                    elif recipe_type == "成品":
                        item_id = self.db_manager.add_product(name, output_quantity)
                        item_type = 'product'
                    else:
                        continue
                    
                    # 处理配方需求（如果CSV中包含需求信息）
                    if 'requirements' in row and row['requirements']:
                        import json
                        requirements = json.loads(row['requirements'])
                        for req in requirements:
                            req_type = req['type']
                            req_name = req['name']
                            req_quantity = req['quantity']
                            
                            if req_type == 'base':
                                material = self.db_manager.get_base_material_by_name(req_name)
                                if material:
                                    self.db_manager.add_recipe_requirement(item_type, item_id, 'base', material['id'], req_quantity)
                            elif req_type == 'material':
                                material = self.db_manager.get_material_by_name(req_name)
                                if material:
                                    self.db_manager.add_recipe_requirement(item_type, item_id, 'material', material['id'], req_quantity)
                    
                    imported_count += 1
                    
                except Exception as e:
                    print(f"导入配方 {row.get('name', '未知')} 失败: {str(e)}")
        
        message = f"导入完成！成功导入 {imported_count} 个配方"
        if skipped_count > 0:
            message += f"，跳过 {skipped_count} 个重复配方"
        
        self.show_message(message, "success")
        self.refresh_recipe_list()
    
    def export_recipes_to_csv(self, file_path: str):
        """导出配方到CSV文件（简化格式）"""
        import csv
        
        # 获取所有配方数据
        recipes = []
        
        # 导出半成品配方
        materials = self.db_manager.get_materials()
        for material in materials:
            requirements = self.db_manager.get_recipe_requirements('material', material['id'])
            
            # 合并所有需求材料
            all_reqs = []
            
            for req in requirements:
                if req['ingredient_type'] == 'base':
                    ingredient = self.db_manager.get_base_material_by_id(req['ingredient_id'])
                    if ingredient:
                        # 格式：名称(数量)，数量为整数
                        quantity = int(req['quantity'])
                        if quantity == 1:
                            all_reqs.append(ingredient['name'])
                        else:
                            all_reqs.append(f"{ingredient['name']}({quantity})")
                else:
                    ingredient = self.db_manager.get_material_by_id(req['ingredient_id'])
                    if ingredient:
                        # 格式：名称(数量)，数量为整数
                        quantity = int(req['quantity'])
                        if quantity == 1:
                            all_reqs.append(ingredient['name'])
                        else:
                            all_reqs.append(f"{ingredient['name']}({quantity})")
            
            recipes.append({
                '物品名称': material['name'],
                '物品类型': '半成品',
                '所需材料': ' '.join(all_reqs) if all_reqs else ''
            })
        
        # 导出成品配方
        products = self.db_manager.get_products()
        for product in products:
            requirements = self.db_manager.get_recipe_requirements('product', product['id'])
            
            # 合并所有需求材料
            all_reqs = []
            
            for req in requirements:
                if req['ingredient_type'] == 'base':
                    ingredient = self.db_manager.get_base_material_by_id(req['ingredient_id'])
                    if ingredient:
                        # 格式：名称(数量)，数量为整数
                        quantity = int(req['quantity'])
                        if quantity == 1:
                            all_reqs.append(ingredient['name'])
                        else:
                            all_reqs.append(f"{ingredient['name']}({quantity})")
                else:
                    ingredient = self.db_manager.get_material_by_id(req['ingredient_id'])
                    if ingredient:
                        # 格式：名称(数量)，数量为整数
                        quantity = int(req['quantity'])
                        if quantity == 1:
                            all_reqs.append(ingredient['name'])
                        else:
                            all_reqs.append(f"{ingredient['name']}({quantity})")
            
            recipes.append({
                '物品名称': product['name'],
                '物品类型': '成品',
                '所需材料': ' '.join(all_reqs) if all_reqs else ''
            })
        
        # 写入CSV文件
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['物品名称', '物品类型', '所需材料']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(recipes)
            
            self.show_message(f"成功导出 {len(recipes)} 个配方到 {file_path}", "success")
        except PermissionError:
            raise PermissionError(f"无法写入文件 {file_path}，请检查文件权限或确保文件未被其他程序占用")
        except Exception as e:
            raise Exception(f"写入CSV文件时发生错误: {str(e)}")
    
    def batch_import_recipes(self):
        """批量导入配方"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配方文件", "", "JSON文件 (*.json);;CSV文件 (*.csv)"
        )
        if file_path:
            try:
                if file_path.endswith('.json'):
                    self.import_recipes_from_json(file_path)
                elif file_path.endswith('.csv'):
                    self.import_recipes_from_csv(file_path)
                else:
                    self.show_message("不支持的文件格式", "error")
            except Exception as e:
                self.show_message(f"批量导入失败: {str(e)}", "error")
    
    def import_recipes_from_json(self, file_path: str):
        """从JSON文件导入配方"""
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        
        imported_count = 0
        for recipe in recipes:
            try:
                name = recipe['name']
                recipe_type = recipe['type']
                output_quantity = recipe.get('output_quantity', 1)
                requirements = recipe.get('requirements', [])
                
                # 添加物品
                if recipe_type == "半成品":
                    item_id = self.db_manager.add_material(name, output_quantity)
                    item_type = 'material'
                else:
                    item_id = self.db_manager.add_product(name, output_quantity)
                    item_type = 'product'
                
                # 添加配方需求
                for req in requirements:
                    req_type = req['type']
                    req_name = req['name']
                    req_quantity = req['quantity']
                    
                    if req_type == 'base':
                        material = self.db_manager.get_base_material_by_name(req_name)
                        if material:
                            self.db_manager.add_recipe_requirement(item_type, item_id, 'base', material['id'], req_quantity)
                    elif req_type == 'material':
                        material = self.db_manager.get_material_by_name(req_name)
                        if material:
                            self.db_manager.add_recipe_requirement(item_type, item_id, 'material', material['id'], req_quantity)
                
                imported_count += 1
            except Exception as e:
                print(f"导入配方 {recipe.get('name', '未知')} 失败: {str(e)}")
        
        self.show_message(f"成功导入 {imported_count} 个配方", "success")
        self.refresh_recipe_list()
        self.refresh_item_list()
    
    def _detect_file_encoding(self, file_path: str) -> str:
        """检测文件编码"""
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'big5', 'latin1', 'cp1252']
        
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        for encoding in encodings:
            try:
                raw_data.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        
        # 如果都失败了，返回默认编码
        return 'utf-8'
    
    def import_recipes_from_csv(self, file_path: str):
        """从CSV文件导入配方（简化格式）"""
        import csv
        import re
        
        imported_count = 0
        skipped_count = 0
        error_count = 0
        missing_materials = set()
        
        # 检测文件编码
        encoding = self._detect_file_encoding(file_path)
        print(f"检测到文件编码: {encoding}")
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):  # 从第2行开始计数（第1行是标题）
                    try:
                        # 支持新的三列格式
                        name = row.get('物品名称', '').strip()
                        item_type_str = row.get('物品类型', '').strip()
                        materials_str = row.get('所需材料', '').strip()
                        
                        if not name:
                            skipped_count += 1
                            continue
                            
                        if not item_type_str:
                            print(f"第{row_num}行：物品'{name}'缺少物品类型")
                            error_count += 1
                            continue
                        
                        # 验证物品类型
                        if item_type_str not in ['成品', '半成品']:
                            print(f"第{row_num}行：物品'{name}'的类型'{item_type_str}'无效，应为'成品'或'半成品'")
                            error_count += 1
                            continue
                        
                        # 确定物品类型
                        is_product = (item_type_str == '成品')
                        
                        # 检查是否已存在
                        existing_item = None
                        if is_product:
                            existing_item = self.db_manager.get_product_by_name(name)
                        else:
                            existing_item = self.db_manager.get_material_by_name(name)
                        
                        if existing_item:
                            skipped_count += 1
                            continue
                        
                        # 添加物品
                        if is_product:
                            # 成品
                            item_id = self.db_manager.add_product(name, 1)
                            item_type = 'product'
                        else:
                            # 半成品
                            item_id = self.db_manager.add_material(name, 1)
                            item_type = 'material'
                        
                        # 解析并添加所需材料
                        if materials_str:
                            materials = self._parse_requirements(materials_str)
                            for mat_name, quantity in materials:
                                # 先尝试作为半成品查找
                                material = self.db_manager.get_material_by_name(mat_name)
                                if material:
                                    self.db_manager.add_recipe_requirement(item_type, item_id, 'material', material['id'], quantity)
                                else:
                                    # 再尝试作为原料查找
                                    base_material = self.db_manager.get_base_material_by_name(mat_name)
                                    if base_material:
                                        self.db_manager.add_recipe_requirement(item_type, item_id, 'base', base_material['id'], quantity)
                                    else:
                                        missing_materials.add(mat_name)
                        
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"第{row_num}行：导入配方 {row.get('物品名称', '未知')} 失败: {str(e)}")
                        error_count += 1
        
        except Exception as e:
            self.show_message(f"读取CSV文件失败: {str(e)}", "error")
            return
        
        # 构建结果消息
        message_parts = []
        if imported_count > 0:
            message_parts.append(f"成功导入 {imported_count} 个配方")
        if skipped_count > 0:
            message_parts.append(f"跳过 {skipped_count} 个重复或空白配方")
        if error_count > 0:
            message_parts.append(f"失败 {error_count} 个配方")
        
        message = "，".join(message_parts) if message_parts else "没有导入任何配方"
        
        # 显示缺失材料警告
        if missing_materials:
            missing_list = list(missing_materials)[:10]  # 只显示前10个
            warning_msg = f"以下材料在数据库中不存在：{', '.join(missing_list)}"
            if len(missing_materials) > 10:
                warning_msg += f" 等{len(missing_materials)}种材料"
            warning_msg += "\n\n请先添加这些材料到数据库中。"
            self.show_message(warning_msg, "warning")
        
        self.refresh_recipe_list()
        self.show_message(f"配方导入完成！{message}", "success" if imported_count > 0 else "warning")
    
    def _parse_requirements(self, requirements_str: str):
        """解析需求字符串，返回(名称, 数量)的列表"""
        import re
        
        if not requirements_str.strip():
            return []
        
        requirements = []
        # 按空格分割
        items = requirements_str.split()
        
        for item in items:
            item = item.strip()
            if not item:
                continue
            
            # 检查是否有数量格式：名称(数量)
            match = re.match(r'^(.+?)\((\d+)\)$', item)
            if match:
                name = match.group(1).strip()
                quantity = int(match.group(2))
            else:
                # 没有括号，默认数量为1
                name = item
                quantity = 1
            
            requirements.append((name, quantity))
        
        return requirements
    
    def refresh_data_stats(self):
        """刷新数据统计"""
        try:
            base_materials = self.db_manager.get_base_materials()
            materials = self.db_manager.get_materials()
            products = self.db_manager.get_products()
            
            stats_text = f"数据统计:\n"
            stats_text += f"• 原材料: {len(base_materials)} 种\n"
            stats_text += f"• 半成品: {len(materials)} 种\n"
            stats_text += f"• 成品: {len(products)} 种\n"
            stats_text += f"• 总计: {len(base_materials) + len(materials) + len(products)} 种物品"
            
            self.stats_label.setText(stats_text)
        except Exception as e:
            self.stats_label.setText(f"统计信息加载失败: {str(e)}")
    
    def validate_data(self):
        """验证数据完整性"""
        try:
            issues = []
            
            # 检查半成品配方
            materials = self.db_manager.get_materials()
            for material in materials:
                requirements = self.db_manager.get_recipe_requirements('material', material['id'])
                if not requirements:
                    issues.append(f"半成品 '{material['name']}' 缺少配方需求")
            
            # 检查成品配方
            products = self.db_manager.get_products()
            for product in products:
                requirements = self.db_manager.get_recipe_requirements('product', product['id'])
                if not requirements:
                    issues.append(f"成品 '{product['name']}' 缺少配方需求")
            
            if issues:
                issue_text = "\n".join(issues[:10])  # 只显示前10个问题
                if len(issues) > 10:
                    issue_text += f"\n... 还有 {len(issues) - 10} 个问题"
                
                dialog = QMessageBox(self)
                dialog.setWindowTitle("数据验证结果")
                dialog.setIcon(QMessageBox.Warning)
                dialog.setText(f"发现 {len(issues)} 个数据问题:")
                dialog.setDetailedText(issue_text)
                dialog.exec()
            else:
                self.show_message("数据验证通过，没有发现问题", "success")
                
        except Exception as e:
            self.show_message(f"数据验证失败: {str(e)}", "error")
    
    def clear_all_data(self):
        """清空所有数据"""
        reply = QMessageBox.question(
            self, "危险操作", 
            "确定要清空所有数据吗？\n\n这将删除所有原材料、半成品、成品和配方数据，此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 清空所有表
                self.db_manager.clear_all_data()
                
                self.show_message("所有数据已清空", "success")
                self.refresh_recipe_list()
                self.refresh_item_list()
                self.refresh_data_stats()
                
                # 清空选中的物品列表
                self.selected_items.clear()
                self.refresh_selected_items()
                
                # 清空结果显示
                self.result_table.setRowCount(0)
                self.recipe_tree.clear()
                self.result_label.setText("计算结果将在这里显示")
                
            except Exception as e:
                self.show_message(f"清空数据失败: {str(e)}", "error")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("FFXIV配方计算器")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("FFXIV Tools")
    
    # 创建主窗口
    window = FFXIVCalculatorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()