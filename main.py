import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QListWidget, 
                               QSpinBox, QProgressBar, QFileDialog, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer

class IconConverter:
    """SVG 到 ICO 的核心转换引擎"""
    
    @staticmethod
    def convert_single(input_path: str, output_path: str, size: int = 256) -> bool:
        if not os.path.exists(input_path):
            return False
            
        renderer = QSvgRenderer(input_path)
        if not renderer.isValid():
            return False
        
        image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()
        
        return image.save(output_path, "ICO")


class WorkerThread(QThread):
    """后台批量转换线程，避免阻塞主 UI 线程"""
    
    progress_updated = Signal(int)
    finished_signal = Signal(int, int)

    def __init__(self, file_paths, output_dir, size):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.size = size

    def run(self):
        success_count = 0
        fail_count = 0
        total = len(self.file_paths)

        for i, input_path in enumerate(self.file_paths):
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            
            if self.output_dir:
                output_path = os.path.join(self.output_dir, f"{base_name}.ico")
            else:
                output_path = os.path.join(os.path.dirname(input_path), f"{base_name}.ico")

            if IconConverter.convert_single(input_path, output_path, self.size):
                success_count += 1
            else:
                fail_count += 1

            progress = int(((i + 1) / total) * 100)
            self.progress_updated.emit(progress)

        self.finished_signal.emit(success_count, fail_count)


class MainWindow(QMainWindow):
    """程序主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Iconify - SVG to ICO Converter")
        self.resize(650, 550)
        
        self.file_paths = []
        self.custom_output_dir = ""
        
        self.setup_ui()
        self.apply_styles()
        self.bind_events()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # 标题区
        title_label = QLabel("SVG to ICO 批量转换工具")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 文件列表区
        self.btn_add_files = QPushButton("添加 SVG 文件")
        self.btn_add_files.setFixedHeight(45)
        main_layout.addWidget(self.btn_add_files)

        self.file_list = QListWidget()
        main_layout.addWidget(self.file_list)

        # 参数设置区
        settings_frame = QFrame()
        settings_layout = QHBoxLayout(settings_frame)
        settings_layout.setContentsMargins(0, 10, 0, 10)
        
        lbl_size = QLabel("输出尺寸:")
        self.spin_size = QSpinBox()
        self.spin_size.setRange(16, 1024)
        self.spin_size.setValue(256)
        self.spin_size.setSuffix(" px")
        
        settings_layout.addWidget(lbl_size)
        settings_layout.addWidget(self.spin_size)
        settings_layout.addStretch()
        main_layout.addWidget(settings_frame)

        # 输出路径区
        output_layout = QHBoxLayout()
        self.lbl_output_dir = QLabel("输出目录: 默认 (与原文件同目录)")
        self.btn_change_dir = QPushButton("更改目录")
        output_layout.addWidget(self.lbl_output_dir)
        output_layout.addStretch()
        output_layout.addWidget(self.btn_change_dir)
        main_layout.addLayout(output_layout)

        # 进度与执行区
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.setFixedHeight(50)
        self.btn_convert.setObjectName("convertButton")
        main_layout.addWidget(self.btn_convert)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #F8F9FA; font-family: 'Microsoft YaHei', sans-serif; font-size: 14px; color: #343A40; }
            QPushButton { background-color: #E9ECEF; border: 1px solid #CED4DA; border-radius: 8px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #DEE2E6; border: 1px solid #ADB5BD; }
            QPushButton#convertButton { background-color: #4DABF7; color: white; font-size: 16px; border: none; }
            QPushButton#convertButton:hover { background-color: #339AF0; }
            QPushButton:disabled { background-color: #E9ECEF; color: #ADB5BD; }
            QListWidget { background-color: white; border: 1px solid #CED4DA; border-radius: 8px; padding: 5px; }
            QSpinBox { padding: 5px; border: 1px solid #CED4DA; border-radius: 5px; background-color: white; }
            QProgressBar { border: 1px solid #CED4DA; border-radius: 5px; text-align: center; background-color: white; }
            QProgressBar::chunk { background-color: #51CF66; border-radius: 4px; }
        """)

    def bind_events(self):
        self.btn_add_files.clicked.connect(self.action_add_files)
        self.btn_change_dir.clicked.connect(self.action_change_dir)
        self.btn_convert.clicked.connect(self.action_start_conversion)

    def action_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择 SVG 文件", "", "SVG Images (*.svg)")
        if files:
            for file in files:
                if file not in self.file_paths:
                    self.file_paths.append(file)
                    self.file_list.addItem(os.path.basename(file))
            self.btn_add_files.setText(f"已添加 {len(self.file_paths)} 个文件 (继续添加)")

    def action_change_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.custom_output_dir = directory
            self.lbl_output_dir.setText(f"输出目录: {self.custom_output_dir}")

    def action_start_conversion(self):
        if not self.file_paths:
            QMessageBox.warning(self, "提示", "请先添加待转换的 SVG 文件。")
            return

        self.btn_add_files.setEnabled(False)
        self.btn_change_dir.setEnabled(False)
        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("转换中...")
        self.progress_bar.setValue(0)

        size = self.spin_size.value()
        self.worker = WorkerThread(self.file_paths, self.custom_output_dir, size)
        
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_conversion_finished)
        self.worker.start()

    def on_conversion_finished(self, success_count, fail_count):
        self.btn_add_files.setEnabled(True)
        self.btn_change_dir.setEnabled(True)
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("开始转换")

        msg = f"转换完成\n\n成功: {success_count}\n失败: {fail_count}"
        QMessageBox.information(self, "任务结束", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())