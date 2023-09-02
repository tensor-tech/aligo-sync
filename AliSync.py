import io
import json
import logging
import os.path
import platform
import subprocess
import sys
import pathlib

from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QProcess, QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QPushButton, QLineEdit, QFormLayout, QApplication, \
    QFileDialog, QSystemTrayIcon, QAction, QMenu, QMessageBox
from aligo import Aligo


class MyLineEdit(QLineEdit):
    clicked = pyqtSignal()  # 定义clicked信号

    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.clicked.emit()  # 发送clicked信号


class Thread(QThread):
    def __init__(self, syncDir):
        super(Thread, self).__init__()
        self.syncDir = syncDir

    def run(self):
        logger = logging.getLogger("aligo")
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        logPath = os.path.join(str(pathlib.Path.home()), ".aligo", "aligo-gui.log")
        fh = logging.FileHandler(filename=logPath, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
        ali = Aligo(level=logging.ERROR)
        file = ali.get_folder_by_path(path="/" + os.path.basename(self.syncDir), create_folder=True)
        ali.sync_folder(local_folder=self.syncDir, remote_folder=file.file_id, flag=True)


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        homedir = str(pathlib.Path.home())
        path = os.path.join(homedir, ".aligo", "gui.json")
        if os.path.exists(path):
            print("读取配置文件")
            self.readConf()

        # 初始化变量
        self.Icon = None
        self.tray = None
        self.p = None
        self.syncDir = os.path.dirname(__file__)
        self.flag = True
        self.period = None
        self.thread = None

        homedir = str(pathlib.Path.home())
        path = os.path.join(homedir, ".aligo", "gui.json")
        if os.path.exists(path):
            print("读取配置文件")
            self.readConf()

        # 初始化组件
        self.timer = None
        self.logBtn = None
        self.syncBtn = None
        self.periodicLine = None
        self.pickLine = None
        self.initUi()

        self.initTray()

        self.initTimer()

        # 链接槽函数
        self.pickLine.clicked.connect(self.selectSyncFolder)
        self.syncBtn.clicked.connect(self.startSync)
        self.timer.timeout.connect(self.startAligo)
        self.logBtn.clicked.connect(self.openLogFile)

    def readConf(self):
        homedir = str(pathlib.Path.home())
        path = os.path.join(homedir, ".aligo", "gui.json")
        with open(path, 'r') as load_f:
            conf = json.load(load_f)
            self.syncDir = conf['path']
            self.period = conf['period']

    def writeConf(self):
        homedir = str(pathlib.Path.home())
        path = os.path.join(homedir, ".aligo", "gui.json")
        d = {"path": self.syncDir, "period": self.period}
        with open(path, 'w') as load_f:
            json.dump(d, load_f)

    def initUi(self):
        # 表格布局
        qfl = QFormLayout()
        # first row
        self.pickLine = MyLineEdit(self.syncDir)
        qfl.addRow("同步文件夹：", self.pickLine)

        # second row
        self.periodicLine = QLineEdit(self.period)
        qfl.addRow("同步周期(分钟)：", self.periodicLine)

        # third row
        self.syncBtn = QPushButton("同步")
        self.logBtn = QPushButton("日志")
        qfl.addRow(self.logBtn, self.syncBtn)

        # 组件设置布局
        self.setLayout(qfl)

    def initTray(self):
        self.tray = QSystemTrayIcon()
        self.Icon = QIcon(get_resource_path("img/sync.ico"))
        self.tray.setIcon(self.Icon)
        showAction = QAction("&显示", self, triggered=self.Show)
        quitAction = QAction("&退出", self, triggered=self.Exit)
        self.trayMenu = QMenu(self)
        self.trayMenu.addAction(showAction)
        self.trayMenu.addSeparator()
        self.trayMenu.addAction(quitAction)
        self.tray.setContextMenu(self.trayMenu)
        self.tray.show()

    def Exit(self):
        # 点击关闭按钮或者点击退出事件会出现图标无法消失的bug，需要手动将图标内存清除
        self.tray = None
        sys.exit(app.exec_())

    def Show(self):
        self.show()

    def closeEvent(self, event):
        if self.tray.isVisible():
            QMessageBox.information(
                self, "系统托盘", "程序将继续在系统托盘中运行。要终止该程序，请在系统托盘条目的上下文菜单中选择[退出]。")
            self.hide()

    def selectSyncFolder(self):
        self.syncDir = QFileDialog.getExistingDirectory(self, "选取文件夹", "./")
        self.pickLine.setText(os.path.basename(self.syncDir))

    def startAligo(self):
        print("启动 aligo")

        self.thread = Thread(self.syncDir)
        self.thread.start()

    def initTimer(self):
        self.timer = QTimer(self)  # 初始化一个定时器

    def startSync(self):
        if self.flag:
            self.flag = False
            self.period = self.periodicLine.text()
            self.timer.start(int(self.period) * 60 * 1000)
            self.syncBtn.setText("停止同步..")
            self.syncBtn.setStyleSheet('''QPushButton{background:red;}''')
            self.writeConf()
            self.startAligo()

        else:
            self.flag = True
            self.timer.stop()
            self.syncBtn.setText("同步")
            self.syncBtn.setStyleSheet(None)

    def openLogFile(self):
        homeDir = str(pathlib.Path.home())
        logPath = os.path.join(homeDir, ".aligo", "aligo-gui.log")
        print(logPath)
        sysstr = platform.system()
        print(sysstr)
        if sysstr == "Windows":
            print("进入windows")
            os.startfile(logPath)
        elif sysstr == "Linux":
            subprocess.call(["xdg-open", logPath])


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    QApplication.setQuitOnLastWindowClosed(False)

    app = QApplication(sys.argv)
    win = MainWindow()
    win.setWindowTitle("阿里云盘同步")
    win.setWindowIcon(QIcon(get_resource_path("img/sync.svg")))
    win.show()
    sys.exit(app.exec_())
