import pyqtgraph as pg

import random

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

from UI.Dashboard import Ui_Dashboard
from Widgets.Widgets import *

def generate_test_data(num_points=100):
    base_lon = 113.325
    base_lat = 23.135

    gps_points = []
    for i in range(num_points):
        r1 = random.uniform(0, 100)
        r2 = random.uniform(0, 100)
        # Simulate a path: longitude and latitude increment slightly
        lon = base_lon + (r1 * 0.0005)
        lat = base_lat + (r2 * 0.0003)

        # Generate temperature: mostly normal, some faults
        if i % 20 == 0:
            temp = random.uniform(80, 240)  # fault temperature
        else:
            temp = random.uniform(0, 80)  # normal range

        gps_points.append((lon, lat, temp))

    return gps_points


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
        self.ui.setupUi(self)
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
