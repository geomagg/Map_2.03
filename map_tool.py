from PyQt5.QtWidgets import (QMainWindow,QAction, QMenu, QHBoxLayout, QVBoxLayout,
qApp, QApplication, QLabel, QPushButton,QLCDNumber, QSlider, QGridLayout,
QFileDialog, QTextEdit, QFrame, QActionGroup,QMessageBox, QColorDialog, QStatusBar)
from qgis.gui import QgsMapToolIdentify

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from qgis.core import QgsGeometry, QgsPointXY
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand


class ConnectTool(QgsMapToolEmitPoint):
    """ Map tool to connect points."""

    line_complete = pyqtSignal(QgsPointXY, QgsPointXY)
    start_point = None
    end_point = None
    rubberband = None

    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, canvas)

    def canvasMoveEvent(self, event):
        if self.start_point:
            point = self.toMapCoordinates(event.pos())
            if self.rubberband:
                self.rubberband.reset()
            else:
                self.rubberband = QgsRubberBand(self.canvas, False)
                self.rubberband.setColor(QColor(Qt.blue))
            # set the geometry for the rubberband
            points = [self.start_point, point]
            self.rubberband.setToGeometry(QgsGeometry.fromPolylineXY(points),
                                          None)

    def canvasPressEvent(self, e):
        if self.start_point is None:
            self.start_point = self.toMapCoordinates(e.pos())
#            print("start point",self.start_point)
        else:
            self.end_point = self.toMapCoordinates(e.pos())
#            print("end point", self.end_point)
            # kill the rubberband
            self.rubberband.reset()
            # line is done, emit a signal
            self.line_complete.emit(self.start_point, self.end_point)
            # reset the points
            self.start_point = None
            self.end_point = None


class infoTool(QgsMapToolIdentify):


    def __init__(self, canvas):

        self.windows =canvas
        QgsMapToolIdentify.__init__(self, canvas)

    def canvasReleaseEvent(self, event):
        found_features = self.identify(event.x(), event.y(),
                                       self.TopDownStopAtFirst,
                                       self.VectorLayer)


        if len(found_features) > 0:
            layer = found_features[0].mLayer
            feature = found_features[0].mFeature
            geometry = feature.geometry()
            info = []
            line = feature.attribute("L")
            station = feature.attribute("S")
            info.append("Line/Station: %d, %d" % (line, station))

            X = geometry.asPoint().x()
            Y  = geometry.asPoint().y()
            info.append("X/Y: %0.1f, %0.1f" % (X, Y))

            QMessageBox.information(self.windows,
                                    "Line & Station",
                                    "\n".join(info))
