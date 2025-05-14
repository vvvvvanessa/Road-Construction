from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QApplication, QWidget, QHBoxLayout, QSizePolicy, QGraphicsView, QGraphicsSimpleTextItem, QGraphicsRectItem, QFileDialog, QGraphicsScene, QListWidget, QListWidgetItem, QToolTip
from PySide6.QtCharts import QChart, QChartView, QScatterSeries, QValueAxis
from PySide6.QtGui import QLinearGradient, QBrush, QColor, QFont, QPainter
import pyqtgraph as pg

import random


pg.setConfigOption('background', 'w')   # 设置图表背景为白色
pg.setConfigOption('foreground', 'k')   # 设置坐标轴/文字为黑色

from UI.Dashboard import Ui_Dashboard

class ColorBarWidget(QGraphicsView):
    def __init__(self, min_temp=0, max_temp=240, width=30, height=200, parent=None):
        super().__init__(parent)

        self.setFixedSize(width + 50, height + 10)  # 给标签留空间

        # 创建场景
        scene = QGraphicsScene()
        self.setScene(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet("background: transparent; border: none")

        # 创建颜色渐变矩形
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor.fromHsv(0, 255, 255))     # 红
        gradient.setColorAt(1, QColor.fromHsv(240, 255, 255))   # 蓝

        rect = QGraphicsRectItem(0, 0, width, height)
        rect.setBrush(QBrush(gradient))
        rect.setPen(Qt.PenStyle.NoPen)
        scene.addItem(rect)

        # 添加最大温度文本
        max_label = QGraphicsSimpleTextItem(f"{max_temp}°C")
        max_label.setFont(QFont("Arial", 10))
        max_label.setPos(width + 5, 0)
        scene.addItem(max_label)

        # 添加最小温度文本
        min_label = QGraphicsSimpleTextItem(f"{min_temp}°C")
        min_label.setFont(QFont("Arial", 10))
        min_label.setPos(width + 5, height - 15)
        scene.addItem(min_label)

        # 设置场景范围
        scene.setSceneRect(QRectF(0, 0, width + 40, height))


def generate_test_data(num_points=100):
    base_lon = 113.325
    base_lat = 23.135

    gps_points = []
    for i in range(num_points):
        # Simulate a path: longitude and latitude increment slightly
        lon = base_lon + (i * 0.0005)
        lat = base_lat + (i * 0.0003)

        # Generate temperature: mostly normal, some faults
        if i % 20 == 0:
            temp = random.uniform(80, 240)  # fault temperature
        else:
            temp = random.uniform(0, 80)  # normal range

        gps_points.append((lon, lat, temp))

    return gps_points

class GPSPlotWidget(QWidget):
    def _on_log_hover(self, item):
        row = self.log_widget.row(item)
        if row in self.anomaly_index_map:
            index = self.anomaly_index_map[row]
            self.highlight_point_by_index(index)

    def widget_connection(self):
        self.log_widget.itemEntered.connect(self._on_log_hover)
        self.log_widget.setMouseTracking(True)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_points = []
        self.anomaly_index_map = {}  # Log item index -> point index
        self.highlight_dot = None  # Highlighter dot

        layout = QHBoxLayout(self)

        self.layout_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.layout_widget, stretch=1)

        # 添加 colorbar 到右侧
        self.colorbar = ColorBarWidget(min_temp=0, max_temp=240, width=20, height=600)
        layout.addWidget(self.colorbar, stretch=0)

        log_group = QGroupBox("Fault Log")
        log_layout = QVBoxLayout()
        self.log_widget = QListWidget()
        log_layout.addWidget(self.log_widget)
        log_group.setLayout(log_layout)

        layout.addWidget(log_group)  # Add to main layout

        # 创建 plot
        self.plot = self.layout_widget.addPlot(row=0, col=0)
        self.plot.setLabel('bottom', 'Longtitude')
        self.plot.setLabel('left', 'Latitude')
        self.plot.addLegend()
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setMenuEnabled(False)
        self.plot.showGrid(x=True, y=True)

        self.layout_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 创建 scatter plot
        self.scatter = pg.ScatterPlotItem(size=10, pen=None, hoverable = True, symbol = 'o', hoverBrush=pg.mkBrush('orange'))
        self.scatter.sigHovered.connect(self.point_hover_event)

        self.plot.addItem(self.scatter)

        self.curve = pg.PlotCurveItem(pen=pg.mkPen(color=(100, 100, 100, 150), width=2))
        self.plot.addItem(self.curve)

        self.widget_connection()

    def highlight_point_by_index(self, data_index):
        lon, lat, temp = self.data_points[data_index]

        if self.highlight_dot:
            self.plot.removeItem(self.highlight_dot)

        self.highlight_dot = pg.ScatterPlotItem([lon], [lat], size=20, brush=pg.mkBrush(QColor(255, 255, 0, 100)), pen = None)
        self.plot.addItem(self.highlight_dot)

        # Center view
        self.plot.vb.setRange(
            xRange=(lon - 0.001, lon + 0.001),
            yRange=(lat - 0.001, lat + 0.001),
            padding=0
        )

    def temp_to_color(self, temp):
        # Clamp temp between 0 and 240
        temp = max(0, min(240, temp))
        # 计算 HSV 色调（240 蓝 → 0 红）
        hue = int(240 - (temp / 240) * 240)
        if 60 < hue < 180:  # filter green-yellow range
            hue = 180 if hue > 120 else 60
        return QColor.fromHsv(hue, 255, 255)

    def point_hover_event(self, points, event):
        if not points:
            QToolTip.hideText()
            return

        point = points[0]
        data = point.data()
        if data and 'temp' in data:
            temp = data['temp']
            pos = event.screenPos()
            QToolTip.showText(pos.toPoint(), f"Temperature: {temp:.1f} °C")

    def update_points(self, gps_data_with_temp):
        if self.highlight_dot:
            self.plot.removeItem(self.highlight_dot)
            self.highlight_dot = None


        self.log_widget.clear()
        self.data_points = gps_data_with_temp
        self.anomaly_index_map = {}

        lons = [lon for lon, lat, temp in gps_data_with_temp]
        lats = [lat for lon, lat, temp in gps_data_with_temp]
        temps = [temp for lon, lat, temp in gps_data_with_temp]

        t_min, t_max = min(temps), max(temps)
        colors = [self.temp_to_color(t) for t in temps]

        # Add points
        spots = [{
            'pos': (lons[i], lats[i]),
            'brush': pg.mkBrush(colors[i]),
            'data': {'temp': temps[i]}  # store temp info
        } for i in range(len(gps_data_with_temp))]

        self.scatter.setData(spots)
        self.curve.setData(x=lons, y=lats)

        # Populate log list and build map
        for i, (lon, lat, temp) in enumerate(gps_data_with_temp):
            if temp >= 70:  # Fault threshold
                log_text = f"[{i + 1}] Fault: {temp:.1f}°C"
                item = QListWidgetItem(log_text)
                self.log_widget.addItem(item)
                self.anomaly_index_map[self.log_widget.count() - 1] = i  # map log item to data point index

        self.plot.setXRange(min(lons) - 0.001, max(lons) + 0.001)
        self.plot.setYRange(min(lats) - 0.001, max(lats) + 0.001)


class InitUI(QWidget):
    def select_pth(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose file")
        self.ui.Disp_pth.setText(folder)

    def change_density(self):
        print("value changed")
        self._density = self.ui.pt_density.currentIndex()

    def process_data(self):
        self.load_data()

    def load_data(self):
        gps_points = generate_test_data(num_points=100)
        self.gps_plot.update_points(gps_points)

    def register_connection(self):
        self.ui.Path_btn.clicked.connect(self.select_pth)
        self.ui.buttonBox.accepted.connect(self.process_data)

    def __init__(self):
        super().__init__()
        self.ui = Ui_Dashboard()
        self.ui.setupUi(self)  # 把 UI 安装到这个 QWidget 上
        self.setMinimumSize(1100, 800)
        self.register_connection()
        self.gps_plot = GPSPlotWidget()
        self.gps_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.ui.gridLayout.addWidget(self.gps_plot)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app = QApplication([])
    dashboard = InitUI()

    dashboard.show()
    app.exec()
