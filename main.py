
import sys
import os
import shutil

from src.gui.main_window import main


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发和PyInstaller打包环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def extract_resource_to_cwd(resource_name, target_name=None):
    """将资源从 _MEIPASS 复制到当前目录"""
    src = resource_path(resource_name)
    if target_name is None:
        target_name = os.path.basename(resource_name)
    dst = os.path.join(os.getcwd(), target_name)
    if os.path.isfile(src) and not os.path.exists(dst):
        shutil.copy(src, dst)


if __name__ == "__main__":
    # 仅在打包环境下释放数据库到根目录
    if hasattr(sys, '_MEIPASS'):
        extract_resource_to_cwd('database/ffixv_recipes.db', 'ffixv_recipes.db')
    main()
