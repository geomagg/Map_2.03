import sys,os
from PyQt5.QtWidgets import (QMainWindow,QAction, QMenu, QHBoxLayout, QVBoxLayout,
                             qApp, QApplication, QLabel, QPushButton,QLCDNumber, QSlider, 
                             QGridLayout,QFileDialog, QTextEdit, QFrame, QActionGroup,
                             QMessageBox, QColorDialog, QStatusBar)
from PyQt5.QtGui import QIcon, QColor, QFont, QPalette
from PyQt5.QtCore import Qt
from qgis.gui import (QgsMapCanvas, QgsMapToolZoom,QgsMapToolPan,QgsMapToolIdentify, 
                      QgisInterface,QgsMapToolIdentify)
from qgis.core import (QgsProject, QgsVectorLayer, QgsPoint, QgsRasterLayer, QgsRaster,
                       QgsDistanceArea,QgsColorRampShader,QgsRasterShader,
                       QgsMarkerSymbol,QgsSingleSymbolRenderer,QgsSingleBandPseudoColorRenderer)
from map_tool import ConnectTool
from map_tool import infoTool
import math
import icons

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("OBN Design")
        self.setGeometry(500, 500, 1400, 800)
        self.project = QgsProject()
        global lay
        lay=[]
#        global curr_dir
#        curr_dir = os.path.dirname(os.path.realpath(__file__))
        self.initUI()

### ---- READING  the file shots.txt, nodes.txt, sail.txt, pol2.txt, pol3.txt, grid.txt

        curr_d = os.path.abspath(os.path.realpath(os.curdir))
        print ('curr_d', curr_d)
        nodespath = "/nodes.txt"
        filename = "file://"+curr_d+nodespath  
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "nodes", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)

        shotspath = "/shots.txt"
        filename = "file://"+curr_d+shotspath   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "shots", "delimitedtext")
        lay.append(layer)

        sailpath = "/sail.txt"
        filename = "file://"+curr_d+sailpath   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "sail", "delimitedtext")
        lay.append(layer)

        gridpath = "/grid.txt"
        filename = "file://"+curr_d+gridpath
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "grid", "delimitedtext")
        lay.append(layer)

        pol2path = "/pol2.txt"
        filename = "file://"+curr_d+pol2path   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "pol2", "delimitedtext")
        lay.append(layer)

        pol3path = "/polshot.txt"
        filename = "file://"+curr_d+pol3path   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "polshot", "delimitedtext")
        lay.append(layer)

###-----------------------------------------------------------------------------------------

    def initUI(self):

        # status bar

        self.statusbar = self.statusBar()
        self.statusbar.showMessage('Ready')

        # Canvas
        frame = QFrame(self)
        self.setCentralWidget(frame)
        self.grid_layout = QGridLayout(frame)
        self.map_canvas = QgsMapCanvas()
        self.grid_layout.addWidget(self.map_canvas)
        self.map_canvas.setCanvasColor(QColor(200, 200,200))

        # coordinates bar
        self.lblXY = QLabel()
        self.lblXY.setFrameStyle(QFrame.Box )
        self.lblXY.setMinimumWidth( 170 )
        self.lblXY.setAlignment( Qt.AlignCenter )
        self.statusbar.setSizeGripEnabled( False )
        self.statusbar.addPermanentWidget( self.lblXY, 0)
        self.map_canvas.xyCoordinates.connect(self.showXY)

        # Water depth  bar
        self.lblDep = QLabel()
        self.lblDep.setFrameStyle( QFrame.StyledPanel )
        self.lblDep.setMinimumWidth( 100 )
        self.statusbar.addPermanentWidget( self.lblDep, 0)
        self.map_canvas.xyCoordinates.connect(self.showDEP)

        # Scale bar 
        self.lblScale = QLabel()
        self.lblScale.setFrameStyle( QFrame.StyledPanel )
        self.lblScale.setMinimumWidth( 140 )
        self.statusbar.addPermanentWidget( self.lblScale, 0 )
        self.map_canvas.scaleChanged.connect(self.showScale)

#  Menu bar
        menubar = self.menuBar()

        #  File
        fileMenu = menubar.addMenu('&File')

        openFile = QAction(QIcon(":/icons/open.png"), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open new File')
        openFile.triggered.connect(self.showDialog)

        exitAct = QAction(QIcon(":/icons/quit.png"), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(qApp.quit)

        fileMenu.addAction(openFile)
        fileMenu.addAction(exitAct)

        #  Layers

        # Shapefiles
        layerMenu = menubar.addMenu('Layers')
        typeMenu = QMenu('Shape_files', self)
        typeMenu1 = QMenu('txtfiles', self)
        typeMenu2 = QMenu('raster files', self)

        readAct = QAction(QIcon(":/icons/nodes.png"), 'Nodes', self)
        readAct.setShortcut('Ctrl+t')
        readAct.setStatusTip('Read Nodes file')
        readAct1 = QAction(QIcon(":/icons/shot.png"),'Shots', self)
        readAct1.setShortcut('Ctrl+n')
        readAct1.setStatusTip('Read Shots file')
        readAct2 = QAction(QIcon(":/icons/sail.png"),'Sail', self)
        readAct2.setShortcut('Ctrl+s')
        readAct2.setStatusTip('Read Sail file')
        readAct3 = QAction(QIcon(":/icons/polygon.png"),'Node Polygon', self)
        readAct3.setShortcut('Ctrl+p')
        readAct3.setStatusTip('Read pol2 file')
        readAct4 = QAction(QIcon(":/icons/polygon.png"),'Shot Polygon', self)
        readAct4.setShortcut('Ctrl+q')
        readAct4.setStatusTip('Read polshot file')
        readAct11 = QAction(QIcon(":/icons/sail.png"),'Grid', self)
        readAct11.setShortcut('Ctrl+a')
        readAct11.setStatusTip('Read Grid file')





        typeMenu.addAction(readAct)
        typeMenu.addAction(readAct1)
        typeMenu.addAction(readAct2)
        typeMenu.addAction(readAct3)
        typeMenu.addAction(readAct4)

        layerMenu.addMenu(typeMenu)
        readAct.triggered.connect(self.ogrNodesInput)
        readAct1.triggered.connect(self.ogrShotsInput)
        readAct2.triggered.connect(self.ogrSailInput)
        readAct3.triggered.connect(self.ogrPol2Input)
        readAct4.triggered.connect(self.ogrPol3Input)
        readAct11.triggered.connect(self.ogrGridInput)


        # txt files
        readAct5 = QAction(QIcon("nodes.png"), 'Nodes', self)
        readAct5.setShortcut('Ctrl+i')
        readAct5.setStatusTip('Read Nodes file')
        readAct6 = QAction(QIcon(":/icons/shot.png"),'Shots', self)
        readAct6.setShortcut('Ctrl+j')
        readAct6.setStatusTip('Read Shots file')
        readAct7 = QAction(QIcon(":/icons/sail.png"),'Sail', self)
        readAct7.setShortcut('Ctrl+k')
        readAct7.setStatusTip('Read Sail file')
        readAct8 = QAction(QIcon(":/icons/polygon.png"),'Node Polygon', self)
        readAct8.setShortcut('Ctrl+l')
        readAct8.setStatusTip('Read pol2 file')
        readAct9 = QAction(QIcon(":/icons/polygon.png"),'Shot Polygon', self)
        readAct9.setShortcut('Ctrl+m')
        readAct9.setStatusTip('Read polshot file')

        readAct12 = QAction(QIcon(":/icons/sail.png"),'Grid', self)
        readAct12.setShortcut('Ctrl+k')
        readAct12.setStatusTip('Read Grid file')


        typeMenu1.addAction(readAct5)
        typeMenu1.addAction(readAct6)
        typeMenu1.addAction(readAct7)
        typeMenu1.addAction(readAct8)
        typeMenu1.addAction(readAct9)

        layerMenu.addMenu(typeMenu1)
        readAct5.triggered.connect(self.txtNodesInput)
        readAct6.triggered.connect(self.txtShotsInput)
        readAct7.triggered.connect(self.txtSailInput)
        readAct8.triggered.connect(self.txtPol2Input)
        readAct9.triggered.connect(self.txtPol3Input)
        readAct12.triggered.connect(self.txtGridInput)

        readAct10 = QAction(QIcon(":/icons/polygon.png"),'Bathymetry raster', self)
        readAct10.setShortcut('Ctrl+e')
        readAct10.setStatusTip('Read bathymetry raster file')

        typeMenu2.addAction(readAct10)

        layerMenu.addMenu(typeMenu2)
        readAct10.triggered.connect(self.rasterBathymetry)


        # View
        viewMenu = menubar.addMenu('View')

       	viewStatAct = QAction('View statusbar', self, checkable=True)
#        exitAct.setShortcut('Ctrl+l')
        viewStatAct.setStatusTip('View statusbar')
        viewStatAct.setChecked(True)
        viewStatAct.triggered.connect(self.toggleMenu)
       	viewMenu.addAction(viewStatAct)

        self.actShowNodesLayer = QAction('View nodes layer', self, checkable=True)
        self.actShowNodesLayer.setStatusTip('View nodes layer')
        self.actShowNodesLayer.setChecked(False)
        self.actShowNodesLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowNodesLayer)

        self.actShowShotsLayer = QAction('View shots layer', self, checkable=True)
        self.actShowShotsLayer.setStatusTip('View shots layer')
        self.actShowShotsLayer.setChecked(False)
        self.actShowShotsLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowShotsLayer)

        self.actShowSailLayer = QAction('View sail layer', self, checkable=True)
        self.actShowSailLayer.setStatusTip('View sail layer')
        self.actShowSailLayer.setChecked(False)
        self.actShowSailLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowSailLayer)

        self.actShowGridLayer = QAction('View grid layer', self, checkable=True)
        self.actShowGridLayer.setStatusTip('View grid layer')
        self.actShowGridLayer.setChecked(False)
        self.actShowGridLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowGridLayer)


        self.actShowPolNodeLayer = QAction('View Polnode layer', self, checkable=True)
        self.actShowPolNodeLayer.setStatusTip('View Polnode layer')
        self.actShowPolNodeLayer.setChecked(False)
        self.actShowPolNodeLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowPolNodeLayer)

        self.actShowPolShotLayer = QAction('View Polshot layer', self, checkable=True)
        self.actShowPolShotLayer.setStatusTip('View Polshot layer')
        self.actShowPolShotLayer.setChecked(False)
        self.actShowPolShotLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowPolShotLayer)

        self.actShowRasterBathyLayer = QAction('View raster bathymetry layer', self, checkable=True)
        self.actShowRasterBathyLayer.setStatusTip('View raster bathymetry layer')
        self.actShowRasterBathyLayer.setChecked(False)
        self.actShowRasterBathyLayer.triggered.connect(self.showLayer) 
        viewMenu.addAction(self.actShowRasterBathyLayer)

        # Layer Preferences
        layerPreferencesMenu = menubar.addMenu('&Layer Preferences')
        nodesTypeMenu = QMenu('Nodes Layer', self)
        shotsTypeMenu = QMenu('Shots Layer', self)
        sailTypeMenu = QMenu('Sail Layer', self)
        polNodesTypeMenu = QMenu('Nodes Polygon Layer', self)

        actPreferencesNodesLayer = QAction('Nodes color', self)
        actPreferencesNodesLayer.setStatusTip('Nodes color')
        nodesTypeMenu.addAction(actPreferencesNodesLayer)
        layerPreferencesMenu.addMenu(nodesTypeMenu)
#        actPreferencesNodesLayer.triggered.connect(self.colorLayerDialog) 


#        actPreferencesShotsLayer = QAction('Trasparency', self)
#        actPreferencesShotsLayer.setStatusTip('Transparency')
#        shotsTypeMenu.addAction(actPreferencesNodesLayer)
#        layerPreferencesMenu.addMenu(shotsTypeMenu)
#        actPreferencesShotsLayer.triggered.connect(self.colorDialog) 

        # Preferences
        preferencesMenu = menubar.addMenu('&Preferences')
        colorAct = QAction(QIcon(":/icons/backgroundcolor.png"), 'Background color', self)
        colorAct.setShortcut('Ctrl+w')
        colorAct.setStatusTip('Background color')
        preferencesMenu.addAction(colorAct)
        colorAct.triggered.connect(self.colorDialog)

        # Computations
        computationsMenu = menubar.addMenu('&Computations')
        compAct = QAction(QIcon('backgroundcolor.png'), 'Total Number of Nodes', self)

        # Help
        helpMenu = menubar.addMenu('&Help')
        helpAct = QAction(QIcon('backgroundcolor.png'), 'About', self)
        helpAct.setStatusTip('Help')
        helpMenu.addAction(helpAct)
 #       helpAct.triggered.connect(self.xxxxxx)

# Tool bar

        self.toolbar = self.addToolBar("Map Tools")

        # Pan
        self.actionPan = QAction(QIcon(":/icons/pan.png"), 'Pan', self)
        self.actionPan.setShortcut("Ctrl+1")
        self.actionPan.setCheckable(True)
        self.actionPan.setStatusTip('Pan mode')
        self.toolbar.addAction(self.actionPan)
        self.actionPan.triggered.connect(self.tool_pan)
        self.tool_pan = QgsMapToolPan(self.map_canvas)

        # Zoom in
        self.actionZoomin = QAction(QIcon(":/icons/zoomin.png"),'Zoom In',self)
        self.actionZoomin.setShortcut("Ctrl+2")
        self.actionZoomin.setCheckable(True)
        viewMenu.addAction(viewStatAct)

        self.actionZoomin.setStatusTip('Zoom in mode')
        self.toolbar.addAction(self.actionZoomin)
        self.actionZoomin.triggered.connect(self.zoom_in)
        self.tool_zoomin = QgsMapToolZoom(self.map_canvas,False)

        # Full zoom
        self.actionFullZoom= QAction(QIcon(":/icons/fullzoom.png"), 'Full Zoom', self)
        self.actionFullZoom.setShortcut("Ctrl+3")
        self.actionFullZoom.setCheckable(True)
        self.actionFullZoom.setStatusTip('Full Zoom  mode')
        self.toolbar.addAction(self.actionFullZoom)
        self.actionFullZoom.triggered.connect(self.zoomExtent)
        self.tool_fullzoom = QgsMapToolZoom(self.map_canvas,False)

        # Zoom out
        self.actionZoomout= QAction(QIcon(":/icons/zoomout.png"), 'Zoom Out', self)
        self.actionZoomout.setShortcut("Ctrl+4")
        self.actionZoomout.setCheckable(True)
        self.actionZoomout.setStatusTip('Zoom Out  mode')
        self.toolbar.addAction(self.actionZoomout)
        self.actionZoomout.triggered.connect(self.zoomOut)
        self.tool_zoomout = QgsMapToolZoom(self.map_canvas,False)

        # Info
        self.actionInfo= QAction(QIcon(":/icons/info.png"), 'Info', self)
        self.actionInfo.setShortcut("Ctrl+5")
        self.actionInfo.setCheckable(True)
        self.actionInfo.setStatusTip('Info mode')
        self.toolbar.addAction(self.actionInfo)
        self.actionInfo.triggered.connect(self.setInfoMode)
        self.tool_info =  infoTool(self.map_canvas)

        # Connect

        self.connect_action = QAction(QIcon(":/icons/distance.png"),"Connect",self)
        self.connect_action.setCheckable(True)
        self.toolbar.addAction(self.connect_action)
        self.connect_action.triggered.connect(self.connect_pt)
        self.tool_connect = ConnectTool(self.map_canvas)
        self.tool_connect.line_complete.connect(self.connect_complete)

        # Exit 
        exitAct1 = QAction(QIcon(":/icons/quit.png"), 'Exit', self)
        exitAct1.setShortcut('Ctrl+Q')
        exitAct1.triggered.connect(qApp.quit)
        exitAct1.setStatusTip('Quit')
        self.toolbar.addAction(exitAct1)
       	self.toolbar = self.addToolBar('Exit')

        # make tools checkable

        tool_group = QActionGroup(self)

        tool_group.addAction(self.actionZoomin)
        tool_group.addAction(self.actionPan)
        tool_group.addAction(self.actionFullZoom)
        tool_group.addAction(self.actionZoomout)
        tool_group.addAction(self.actionInfo)
        tool_group.addAction(self.connect_action)

        # Event

        self.statusBar()

    def showVisibleMapLayers(self):
     lay1=[]
     self.project.instance().addMapLayers(lay)

     if (next((x for x in lay if x.name() == 'nodes'), None)):
       layer=next((x for x in lay if x.name() == 'nodes'), None)
       if self.actShowNodesLayer.isChecked():
         isymbol = QgsMarkerSymbol.createSimple({'color' : "255,0,0",
                  'size' : "5", 'name' : "circle" })
         renderer = QgsSingleSymbolRenderer(isymbol)
         layer.setRenderer(renderer)
         lay1.append(layer)
     else:
       if self.actShowNodesLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Nodes shapefile NOT loaded")
         self.actShowNodesLayer.setChecked(False)

     if (next((x for x in lay if x.name() == 'shots'), None)):
       layer=next((x for x in lay if x.name() == 'shots'), None)
       if self.actShowShotsLayer.isChecked():
         isymbol = QgsMarkerSymbol.createSimple({'color' : "0,0,255",
                  'size' : "4", 'name' : "star" })
         renderer = QgsSingleSymbolRenderer(isymbol)
         layer.setRenderer(renderer)
         lay1.append(layer)

     else:
       if self.actShowShotsLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Shots shapefile NOT loaded")
         self.actShowShotsLayer.setChecked(False)


#PORRA
     if (next((x for x in lay if x.name() == 'sail'), None)):
       layer=next((x for x in lay if x.name() == 'sail'), None)
       if self.actShowSailLayer.isChecked():
          isymbol = QgsMarkerSymbol.createSimple({'color' : "0,100,0",
                  'size' : "5", 'name' : "circle" })
          renderer = QgsSingleSymbolRenderer(isymbol)
          layer.setRenderer(renderer)
          lay1.append(layer)
     else:
       if self.actShowSailLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Sail shapefile NOT loaded")
         self.actShowSailLayer.setChecked(False)



     if (next((x for x in lay if x.name() == 'grid'), None)):
       layer=next((x for x in lay if x.name() == 'grid'), None)
       if self.actShowGridLayer.isChecked():
          isymbol = QgsMarkerSymbol.createSimple({'color' : "255,0,5",
                  'size' : "1", 'name' : "circle" })
          renderer = QgsSingleSymbolRenderer(isymbol)
          layer.setRenderer(renderer)
          lay1.append(layer)
     else:
       if self.actShowGridlLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Grid shapefile NOT loaded")
         self.actShowGridLayer.setChecked(False)






     if (next((x for x in lay if x.name() == 'pol2'), None)):
       layer=next((x for x in lay if x.name() == 'pol2'), None)
       if self.actShowPolNodeLayer.isChecked():
         isymbol = QgsMarkerSymbol.createSimple({'color' : "4,126,14",
                  'size' : "3", 'name' : "triangle" })
         renderer = QgsSingleSymbolRenderer(isymbol)
         layer.setRenderer(renderer)
         lay1.append(layer)
     else:
       if self.actShowPolNodeLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Pol2 shapefile NOT loaded")
         self.actShowPolNodeLayer.setChecked(False)

     if (next((x for x in lay if x.name() == 'polshot'), None)):
       layer=next((x for x in lay if x.name() == 'polshot'), None)
       if self.actShowPolShotLayer.isChecked():
        isymbol = QgsMarkerSymbol.createSimple({'color' : "128,128,255",
                  'size' : "2.5", 'name' : "square" })
        renderer = QgsSingleSymbolRenderer(isymbol)
        layer.setRenderer(renderer)
        lay1.append(layer)
     else:
       if self.actShowPolShotLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Polshot shapefile NOT loaded")
         self.actShowPolShotLayer.setChecked(False)

     # Rasters
     if (next((x for x in lay if x.name() == 'bathymetry'), None)):
       layer=next((x for x in lay if x.name() == 'bathymetry'), None)
       if self.actShowRasterBathyLayer.isChecked():

         fcn = QgsColorRampShader()
         fcn.setColorRampType(QgsColorRampShader.Interpolated)
         lst = [ QgsColorRampShader.ColorRampItem(0, QColor(255,0,0)), \
         QgsColorRampShader.ColorRampItem(50, QColor(255,140,0)), \
         QgsColorRampShader.ColorRampItem(100, QColor(255,250,205)), \
         QgsColorRampShader.ColorRampItem(155, QColor(144,238,144)), \
         QgsColorRampShader.ColorRampItem(255, QColor(100,249,237)) ]

         fcn.setColorRampItemList(lst)
         shader = QgsRasterShader()
         shader.setRasterShaderFunction(fcn)

         renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
         layer.setRenderer(renderer)
         layer.renderer().setOpacity(0.6)

         lay1.append(layer)

     else:
       if self.actShowRasterBathyLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Raster BAthymetry  NOT loaded")
         self.actShowRasterBathyLayer.setChecked(False)

     self.project.instance().addMapLayers(lay1)
     self.map_canvas.setLayers(lay1)


     self.map_canvas.zoomToFullExtent()
###
    def ogrNodesInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
        if path[0]:
           (name, ext) = os.path.basename(path[0]).split('.')
           layer = QgsVectorLayer(path[0], 'nodes', 'ogr')
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED", "Nodes shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Nodes shapefile NOT loaded")
 
    def ogrShotsInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'shots', 'ogr')
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Shots shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Shot shapefile NOT loaded")

    def ogrSailInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'sail', 'ogr')
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Sail shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Sail shapefile NOT loaded")

    def ogrGridInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'grid', 'ogr')
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Grid shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Grid shapefile NOT loaded")





    def ogrPol2Input(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'pol2', 'ogr')
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Pol2 shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Pol2 shapefile NOT loaded")

    def ogrPol3Input(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'pol3', 'ogr')
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Pol3 shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Pol3 shapefile NOT loaded")

    def txtNodesInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
         print ('CXXXXXXXXXXXXXX CARALHO WWWWWW', curr_dir)
         filename = "file://"+path[0]   # os.path.join(cur_dir, ProJect, "nodes.txt")
         print ('filename', filename, path[0])
         uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
         layer = QgsVectorLayer(uri, "nodes", "delimitedtext")
         if layer.isValid():
             lay.append(layer)
             print(layer.name())
             QMessageBox.about(self, "LAYER LOADED!", "Nodes txt layer  loaded")
         else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Nodes txt-delimited NOT loaded")

    def txtShotsInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "shots", "delimitedtext")
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Shots txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Shots txt-delimited NOT loaded")

    def txtSailInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "sail", "delimitedtext")
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Sail txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Sail txt-delimited NOT loaded")

    def txtGridInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "grid", "delimitedtext")
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Grid txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Grid txt-delimited NOT loaded")




    def txtPol2Input(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "pol2", "delimitedtext")
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Pol2 txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Pol2 txt-delimited NOT loaded")

    def txtPol3Input(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "pol3", "delimitedtext")
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Pol3 txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Pol3 txt-delimited NOT loaded")

    def rasterBathymetry(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', curr_dir)
       if path[0]:
           layer = QgsRasterLayer(path[0], "bathymetry")
           if layer.isValid():
             lay.append(layer)
             QMessageBox.about(self, "LAYER LOADED!", "Bathymetry raster layer loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Bathymetry raster NOT loaded")

    def closeEvent(self, event):

       	reply = QMessageBox.question(self, 'Message',
            "Are you sure to quit?", QMessageBox.Yes | 
            QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()        

    def showLayer(self):
        self.showVisibleMapLayers()

    def toggleMenu(self, state):
       	if state:
            self.statusbar.show()
        else:
            self.statusbar.hide()

    def tool_pan(self):
        self.map_canvas.setMapTool(self.tool_pan)
        self.actionPan.setChecked(True)

    def zoom_in(self):
        self.map_canvas.setMapTool(self.tool_zoomin)
        self.actionZoomin.setChecked(True)

    def zoomExtent(self):
        self.map_canvas.zoomToFullExtent()

    def zoomOut(self):
        self.map_canvas.zoomOut()

    def setInfoMode(self):
        self.map_canvas.setMapTool(self.tool_info)

    def contextMenuEvent(self, event):
           cmenu = QMenu(self)
           newAct = cmenu.addAction("New")
           opnAct = cmenu.addAction("Open")
           quitAct = cmenu.addAction("Quit")
           action = cmenu.exec_(self.mapToGlobal(event.pos()))
           if action == quitAct:
              qApp.quit()

    def keyPressEvent(self, e):
       	if e.key() == Qt.Key_Escape:
            self.close()

    def showDialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')
        if fname[0]:
            f = open(fname[0], 'r')

            with f:
                data = f.read()
                self.textEdit.setText(data)    

    def colorDialog(self):

        col = QColorDialog.getColor()

        if col.isValid():
#            self.frame.setStyleSheet("QWidget { background-color: %s }"
#                % col.name())

          self.map_canvas.setCanvasColor(QColor(col))

    def colorLayerDialog(self):

        col= QColorDialog.getColor()
        if col.isValid():
           isymbol = QgsMarkerSymbolV2.createSimple({'color' : col,
                  'size' : "5", 'name' : "circle" })
           renderer = QgsSingleSymbolRendererV2(isymbol)
           self.layer.setRendererV2(renderer)

    def showXY( self, p ):
       """ SLOT. Show coordinates """
       self.lblXY.setText( str(float(p.x())) + " | " + str(float(p.y())) )

    def connect_pt(self):
        self.map_canvas.setMapTool(self.tool_connect)
        self.connect_action.setChecked(True)

    def connect_complete(self, pt1, pt2):

        distance_calc = QgsDistanceArea()
        a=pt1.x()-pt2.x()
        distance = distance_calc.measureLine([pt1,pt2]) / 1000
        angle = math.atan2(pt2.x()-pt1.x(), pt2.y()-pt1.y())
        angle = math.degrees(angle)
        if angle < 0: 
          angle=angle + 360
        QMessageBox.information(None,
                                "Distance and Azimuth",
                                "Distance = %s (Km)                                            Azimuth =  %s (degrees)"
                                % (str(distance), str(angle)))

    def showDEP ( self, p ):
        """ SLOT. SHOW Depth """
        if (next((x for x in lay if x.name() == 'bathymetry'), None)):
          layer=next((x for x in lay if x.name() == 'bathymetry'), None)
          ident = layer.dataProvider().identify(p, QgsRaster.IdentifyFormatValue)
          
          pal = self.lblDep.palette()
          pal.setColor(QPalette.WindowText, QColor("red"))
          self.lblDep.setPalette(pal)

          self.lblDep.setText( str(ident.results()[1]) +  "  m" )
          self.lblDep.setFont(QFont("Arial", 22))


    def showScale( self, scale ):
       """ SLOT. Show scale """
       self.lblScale.setText( "Scale 1:" + str(round(scale)) )
