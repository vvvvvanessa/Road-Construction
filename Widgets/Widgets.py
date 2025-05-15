from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QApplication, QWidget, QHBoxLayout, QSizePolicy, QGraphicsView, \
    QGraphicsSimpleTextItem, QGraphicsRectItem, QFileDialog, QGraphicsScene, QListWidget, QListWidgetItem, QToolTip
from PySide6.QtCharts import QChart, QChartView, QScatterSeries, QValueAxis
from PySide6.QtGui import QLinearGradient, QBrush, QColor, QFont, QPainter
import pyqtgraph as pg

class ColorBarWidget(QGraphicsView):
    def __init__(self, width=30, height=200, parent=None):
        super().__init__(parent)

        self.setFixedSize(width + 50, height + 10)
        self._wid = width
        self._height = height
        scene = QGraphicsScene()
        self.setScene(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet("background: transparent; border: none")

        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor.fromHsv(0, 255, 255))     # Red
        gradient.setColorAt(1, QColor.fromHsv(240, 255, 255))   # Blue

        rect = QGraphicsRectItem(0, 0, width, height)
        rect.setBrush(QBrush(gradient))
        rect.setPen(Qt.PenStyle.NoPen)
        scene.addItem(rect)

        scene.setSceneRect(QRectF(0, 0, width + 40, height))

    def update_value(self, min_temp, max_temp):
        max_label = QGraphicsSimpleTextItem(f"{max_temp}°C")
        max_label.setFont(QFont("Arial", 10))
        max_label.setPos(self._wid + 5, 0)
        self.scene().addItem(max_label)

        min_label = QGraphicsSimpleTextItem(f"{min_temp}°C")
        min_label.setFont(QFont("Arial", 10))
        min_label.setPos(self._wid + 5, self._height- 15)
        self.scene().addItem(min_label)

class GPSPlotWidget(QWidget):

    def _on_log_hover(self, item):
        row = self.log_widget.row(item)
        if row in self.anomaly_index_map:
            index = self.anomaly_index_map[row]
            self.highlight_point_by_index(index)

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

    def widget_connection(self):
        self.log_widget.itemEntered.connect(self._on_log_hover)
        self.log_widget.setMouseTracking(True)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data_points = []
        self.anomaly_index_map = {}  # Log item index -> point index
        self.highlight_dot = None  # Highlighter dot

        layout = QHBoxLayout(self)

        # plot widget
        self.layout_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.layout_widget, stretch=1)
        # Color bar
        self.colorbar = ColorBarWidget(width=20, height=600)
        layout.addWidget(self.colorbar, stretch=0)

        log_group = QGroupBox("Fault Log")
        log_layout = QVBoxLayout()
        self.log_widget = QListWidget()
        log_layout.addWidget(self.log_widget)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)  # Add to main layout

        self.plot = self.layout_widget.addPlot(row=0, col=0)
        self.plot.setLabel('bottom', 'Longtitude')
        self.plot.setLabel('left', 'Latitude')
        self.plot.addLegend()
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setMenuEnabled(False)
        self.plot.showGrid(x=True, y=True)

        self.layout_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Plot temp with scatter plot
        self.scatter = pg.ScatterPlotItem(size=10, pen=None, hoverable = True, symbol = 'o', hoverBrush=pg.mkBrush('orange'))

        self.plot.addItem(self.scatter)

        self.curve = pg.PlotCurveItem(pen=pg.mkPen(color=(100, 100, 100, 150), width=2))
        self.plot.addItem(self.curve)

        self.widget_connection()

    def temp_to_color(self, temp, t_min, t_max):
        # HSV map
        scale = 120/(t_max-t_min)
        hue = int((temp-t_min)*scale + 240)
        return QColor.fromHsv(hue, 255, 255)

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
        colors = [self.temp_to_color(t, t_min, t_max) for t in temps]

        # Add points
        spots = [{
            'pos': (lons[i], lats[i]),
            'brush': pg.mkBrush(colors[i]),
            'data': {'temp=': temps[i]},
            # store temp info
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

        self.colorbar.update_value(t_min, t_max)
