
from PyQt5.QtWidgets import (QMainWindow,QAction, QMenu, QHBoxLayout, QVBoxLayout,
qApp, QApplication, QLabel, QPushButton,QLCDNumber, QSlider, QGridLayout,
QFileDialog, QTextEdit, QFrame, QActionGroup,QMessageBox, QColorDialog, QStatusBar)

from qgis.gui import QgsMapToolIdentify


class infoTool(QgsMapToolIdentify):


    def __init__(self, canvas):

        self.windows =canvas
        QgsMapToolIdentify.__init__(self, canvas)
#        self.window = canvas

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
            print ("     ")
            print (" Line ") , line
            print ("      ")
            print ("Satation"), station
             
            info.append("Line/Station: %d, %d" % (line, station))


            X = geometry.asPoint().x()
            Y  = geometry.asPoint().y()
            info.append("X/Y: %0.1f, %0.1f" % (X, Y))

            QMessageBox.information(self.windows,
                                    "Line & Station",
                                    "\n".join(info))
