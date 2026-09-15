import sys,os,shutil,struct
from PyQt5.QtWidgets import (QMainWindow,QAction, QMenu, QHBoxLayout, QVBoxLayout,
                             qApp, QApplication, QLabel, QPushButton,QLCDNumber, QSlider, 
                             QGridLayout,QFileDialog, QTextEdit, QFrame, QActionGroup,
                             QMessageBox, QColorDialog, QStatusBar, QInputDialog,
                             QDockWidget, QWidget, QProgressDialog, QDialog)
from PyQt5.QtGui import QIcon, QColor, QFont, QPalette
from PyQt5.QtCore import Qt
from qgis.gui import (QgsMapCanvas, QgsMapToolZoom,QgsMapToolPan,QgsMapToolIdentify, 
                      QgisInterface,QgsMapToolIdentify)
from qgis.core import (QgsProject, QgsVectorLayer, QgsPoint, QgsPointXY, QgsRasterLayer, QgsRaster,
                       QgsDistanceArea,QgsColorRampShader,QgsRasterShader,
                       QgsMarkerSymbol,QgsSingleSymbolRenderer,QgsSingleBandPseudoColorRenderer,
                       QgsSpatialIndex,QgsRectangle,QgsFeature,QgsGeometry,
                       QgsFillSymbol,QgsRendererRange,QgsGraduatedSymbolRenderer,
                       QgsSimpleFillSymbolLayer,
                       QgsWkbTypes)
from map_tool import ConnectTool
from map_tool import infoTool
from map_tool import RectSelectTool
import math
import icons

# Binary format for the CMP cache file: 4-byte magic + a fixed header
# (extent + max offset, as 5 doubles) + one 32-byte record (mx,my,offset,
# azimuth as 4 doubles) per source-receiver pair. Reading/writing raw
# bytes like this is much faster than parsing a CSV line by line, and the
# file is smaller on disk too.
CMP_MAGIC = b'CMP1'
CMP_HEADER_FMT = '<5d'   # xmin, xmax, ymin, ymax, max_offset
CMP_HEADER_SIZE = struct.calcsize(CMP_HEADER_FMT)
CMP_RECORD_FMT = '<4d'   # mx, my, offset, azimuth
CMP_RECORD_SIZE = struct.calcsize(CMP_RECORD_FMT)

APP_VERSION = "2.03"
APP_PROJECT = "UFF / SHELL"

HELP_HTML = """
<h2>OBN Design -- Manual rapido</h2>
<p>Ferramenta para desenho e QC de aquisicao sismica OBN: plotagem de nodes,
shots, sail lines e poligonos de area, alem de calculo de fold, azimute e
diagramas offset-azimute.</p>

<h3>Barra de ferramentas</h3>
<ul>
<li><b>Pan / Zoom in / Zoom out / Full extent</b> -- navegacao basica no mapa.</li>
<li><b>Connect</b> -- clique em dois pontos no mapa; mostra distancia (km) e
azimute (graus) entre eles.</li>
<li><b>Select Area</b> -- arraste um retangulo no mapa; mostra quantos
<i>nodes</i> e <i>shots</i> caem dentro dele.</li>
<li><b>Info tool</b> -- clique numa feicao pra ver seus atributos
(linha/estacao, X/Y).</li>
</ul>

<h3>Menu Layers</h3>
<p>Carregar camadas manualmente, por shapefile (<i>Shape_files</i>) ou por
arquivo texto delimitado (<i>txtfiles</i>): Nodes, Shots, Sail, Grid, Node
Polygon, Shot Polygon. Os poligonos (pol2/polshot) sao montados
automaticamente a partir de uma lista ordenada de vertices. Recarregar
qualquer uma dessas camadas <b>substitui</b> a anterior (nao fica a antiga
"escondida" por baixo) e ja exibe a nova automaticamente.</p>
<p><i>nodes.txt</i>, <i>pol2.txt</i> e <i>polshot.txt</i>/<i>pol3.txt</i> sao
carregados e exibidos automaticamente ao abrir o programa, se estiverem na
pasta de dados. Shots/Sail/Grid precisam ser carregados manualmente.</p>

<h3>Menu View</h3>
<p>Checkboxes pra mostrar/esconder cada camada carregada (nodes, shots,
sail, grid, poligonos, raster de batimetria, fold map, azimuth map).</p>

<h3>Menu Layer Preferences</h3>
<p>Cor e tamanho de nodes/shots/sail; cor e espessura de linha dos poligonos;
transparencia e legenda de cores do fold map e do azimuth map.</p>

<h3>Menu Preferences</h3>
<ul>
<li><b>Background color</b> -- cor de fundo do canvas.</li>
<li><b>Diretorio de dados</b> -- pasta padrao aberta pelos dialogos de
"Open file" do menu Layers. Configure aqui a pasta onde estao seus arquivos
de nodes/shots/etc, pra nao precisar navegar toda vez.</li>
</ul>

<h3>Menu Design</h3>
<ul>
<li><b>Gerar Nodes (grid no Poligono)</b> -- cria um grid regular de nodes
dentro do poligono <i>pol2</i> (Node Polygon), a partir do espacamento entre
nodes na linha (X), espacamento entre linhas (Y), e a direcao das linhas
(azimute, 0 = Norte).</li>
<li><b>Gerar Shots (grid no Poligono)</b> -- mesma coisa, mas dentro do
poligono <i>polshot</i> (Shot Polygon), gerando a camada de shots.</li>
</ul>
<p>Ambas tem as mesmas opcoes adicionais:</p>
<ul>
<li><i>Incluir na borda</i> -- inclui pontos que caem exatamente em cima do
contorno do poligono, alem do interior.</li>
<li><i>Alternar (escalonar) entre linhas</i> -- desloca as linhas
alternadas em metade do espacamento X (dx/2), gerando um padrao em
"tijolo" em vez de um grid retangular alinhado.</li>
</ul>
<p>O resultado e salvo como um novo <i>nodes.txt</i>/<i>shots.txt</i> (voce
escolhe onde) e ja carregado automaticamente como a respectiva camada.</p>

<h3>Menu Computations</h3>
<ul>
<li><b>Fold Map</b> -- mapa de fold (cobertura CMP) por bin, numa faixa de
offset escolhida (minimo e maximo).</li>
<li><b>Azimuth Map</b> -- azimute medio (circular) por bin, na mesma logica
de bins do Fold Map.</li>
<li><b>Fold Rose (Azimute)</b> -- diagrama polar offset x azimute: angulo =
azimute (0 = Norte, sentido horario), raio = offset (aneis), cor = fold.
Requer a biblioteca <i>matplotlib</i> instalada no Python do QGIS.</li>
<li><b>Arquivo CMP</b> -- cache em disco (formato binario .cmp, compacto e
rapido de ler/escrever) dos pares fonte-receptor (midpoint, offset,
azimute). Gerado e atualizado automaticamente na primeira vez que voce
calcula Fold/Azimuth/Rose; calculos seguintes com offset menor ou igual ao
ja calculado reaproveitam o arquivo, sem refazer a busca espacial nem
estourar memoria em levantamentos grandes (os pares sao gravados direto no
disco conforme sao calculados, nunca ficam todos na RAM de uma vez). O
cache e reconhecido automaticamente entre sessoes (mesmo fechando e
reabrindo o programa) e e invalidado sozinho se voce recarregar
nodes/shots com dados diferentes. Normalmente voce nao precisa mexer
neste submenu -- ele existe pra quem quiser gerar/salvar/carregar o cache
manualmente.</li>
</ul>

<h3>Dica de fluxo de trabalho</h3>
<ol>
<li>Configure o <b>Diretorio de dados</b> (Preferences) apontando pra pasta
dos seus arquivos.</li>
<li>Carregue Nodes, Shots (e Sail/Grid se precisar) pelo menu Layers -- ou
use <b>Design > Gerar Nodes</b> pra criar um grid novo dentro do poligono.</li>
<li>Ajuste cores/tamanhos em Layer Preferences, se quiser.</li>
<li>Calcule Fold Map, Azimuth Map ou Fold Rose em Computations -- o cache

CMP cuida de deixar os calculos seguintes rapidos.</li>
</ol>
"""

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("OBN Design v%s" % APP_VERSION)
        self.setGeometry(500, 500, 1400, 800)
        self.project = QgsProject()
        global curr_dir
        curr_dir = os.path.dirname(os.path.realpath(__file__))

        # default folder shown by the "Open file" dialogs (Layers menu).
        # Change it via Preferences > Diretorio de dados.
        self.data_dir = curr_dir

        # default layer styling (color/size), can be changed via Layer Preferences menu
        self.nodesColor = QColor(255, 0, 0)
        self.nodesSize = 5
        self.shotsColor = QColor(0, 0, 255)
        self.shotsSize = 4
        self.sailColor = QColor(0, 100, 0)
        self.sailSize = 3
        self.polNodeColor = QColor(4, 126, 14)
        self.polNodeOutlineWidth = 0.5
        self.polShotColor = QColor(128, 128, 255)
        self.polShotOutlineWidth = 0.5
        self.foldOpacity = 0.6
        self.foldRanges = []
        self.azimuthOpacity = 0.6
        self.azimuthRanges = []
        self.cmp_file = None        # path to the on-disk CMP cache (mx,my,offset,azimuth), or None
        self.cmp_max_offset = None  # max offset covered by self.cmp_file
        self.cmp_extent = None      # (xmin, xmax, ymin, ymax) of nodes+shots, for stable binning
        self.pairs_error = None
        self.pairs_canceled = False
        self.pairs_from_cache = False

        self.initUI()

### ---- READING  the file shots.txt, nodes.txt, sail.txt, pol2.txt, pol3.txt, grid.txt

        global lay
        lay=[]

        curr_d = os.path.abspath(os.path.realpath(os.curdir))
        print ('curr_d', curr_d)
        nodespath = "/nodes.txt"
        filename = "file://"+curr_d+nodespath  
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "nodes", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)

        # shots.txt, sail.txt e grid.txt NAO sao carregados automaticamente no
        # startup por escolha do usuario -- use os menus Layers > Shape_files
        # ou Layers > txtfiles para carrega-los manualmente quando precisar.

        pol2path = "/pol2.txt"
        filename = "file://"+curr_d+pol2path   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        raw_layer = QgsVectorLayer(uri, "pol2", "delimitedtext")
        if raw_layer.isValid():
            poly_layer = self.toPolygonLayer(raw_layer, "pol2")
            lay.append(poly_layer if poly_layer else raw_layer)
        else:
            lay.append(raw_layer)

        pol3path = "/polshot.txt"
        filename = "file://"+curr_d+pol3path   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        raw_layer = QgsVectorLayer(uri, "polshot", "delimitedtext")
        if not raw_layer.isValid():
            # fallback: some setups name this file "pol3.txt" instead of "polshot.txt"
            pol3path_alt = "/pol3.txt"
            filename = "file://"+curr_d+pol3path_alt
            uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
            raw_layer = QgsVectorLayer(uri, "polshot", "delimitedtext")
        if raw_layer.isValid():
            poly_layer = self.toPolygonLayer(raw_layer, "polshot")
            lay.append(poly_layer if poly_layer else raw_layer)
        else:
            lay.append(raw_layer)

        # show nodes + the two polygons automatically at startup; the user
        # loads shots/sail/grid manually afterwards via the Layers menu
        self.actShowNodesLayer.setChecked(True)
        self.actShowPolNodeLayer.setChecked(True)
        self.actShowPolShotLayer.setChecked(True)
        self.showVisibleMapLayers()

        # reuse a CMP cache left over from a previous run, if one exists
        # in the data folder (silent -- no popup at startup)
        self._tryAutoLoadCMPCache(notify=False)

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
        # performance: cache each layer's rendered image and reuse it across
        # zoom/pan when the data hasn't changed, and render layers in parallel
        # -- helps a lot with layers that have many points (like shots)
        self.map_canvas.setCachingEnabled(True)
        self.map_canvas.setParallelRenderingEnabled(True)
#
#
        # Fold map legend dock (hidden by default)
        self.foldLegendDock = QDockWidget("Fold Map - Legenda", self)
        self.foldLegendWidget = QWidget()
        self.foldLegendLayout = QVBoxLayout()
        self.foldLegendWidget.setLayout(self.foldLegendLayout)
        self.foldLegendDock.setWidget(self.foldLegendWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.foldLegendDock)
        self.foldLegendDock.hide()

        # Azimuth map legend dock (hidden by default)
        self.azimuthLegendDock = QDockWidget("Azimuth Map - Legenda", self)
        self.azimuthLegendWidget = QWidget()
        self.azimuthLegendLayout = QVBoxLayout()
        self.azimuthLegendWidget.setLayout(self.azimuthLegendLayout)
        self.azimuthLegendDock.setWidget(self.azimuthLegendWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.azimuthLegendDock)
        self.azimuthLegendDock.hide()

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
        typeMenu.addAction(readAct11)

        layerMenu.addMenu(typeMenu)
        readAct.triggered.connect(self.ogrNodesInput)
        readAct1.triggered.connect(self.ogrShotsInput)
        readAct2.triggered.connect(self.ogrSailInput)
        readAct3.triggered.connect(self.ogrPol2Input)
        readAct4.triggered.connect(self.ogrPol3Input)
        readAct11.triggered.connect(self.ogrGridInput)


        # txt files
        readAct5 = QAction(QIcon(":/icons/nodes.png"), 'Nodes', self)
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
        typeMenu1.addAction(readAct12)

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

        self.actShowFoldLayer = QAction('View fold map layer', self, checkable=True)
        self.actShowFoldLayer.setStatusTip('View fold map layer')
        self.actShowFoldLayer.setChecked(False)
        self.actShowFoldLayer.triggered.connect(self.showLayer)
        viewMenu.addAction(self.actShowFoldLayer)

        self.actShowAzimuthLayer = QAction('View azimuth map layer', self, checkable=True)
        self.actShowAzimuthLayer.setStatusTip('View azimuth map layer')
        self.actShowAzimuthLayer.setChecked(False)
        self.actShowAzimuthLayer.triggered.connect(self.showLayer)
        viewMenu.addAction(self.actShowAzimuthLayer)

        # Layer Preferences
        layerPreferencesMenu = menubar.addMenu('&Layer Preferences')
        nodesTypeMenu = QMenu('Nodes Layer', self)
        shotsTypeMenu = QMenu('Shots Layer', self)
        sailTypeMenu = QMenu('Sail Layer', self)
        polNodesTypeMenu = QMenu('Nodes Polygon Layer', self)

        # Nodes: color + size
        actPreferencesNodesColor = QAction('Cor', self)
        actPreferencesNodesColor.setStatusTip('Nodes color')
        nodesTypeMenu.addAction(actPreferencesNodesColor)
        actPreferencesNodesColor.triggered.connect(self.setNodesColor)

        actPreferencesNodesSize = QAction('Tamanho', self)
        actPreferencesNodesSize.setStatusTip('Nodes size')
        nodesTypeMenu.addAction(actPreferencesNodesSize)
        actPreferencesNodesSize.triggered.connect(self.setNodesSize)

        layerPreferencesMenu.addMenu(nodesTypeMenu)

        # Shots: color + size
        actPreferencesShotsColor = QAction('Cor', self)
        actPreferencesShotsColor.setStatusTip('Shots color')
        shotsTypeMenu.addAction(actPreferencesShotsColor)
        actPreferencesShotsColor.triggered.connect(self.setShotsColor)

        actPreferencesShotsSize = QAction('Tamanho', self)
        actPreferencesShotsSize.setStatusTip('Shots size')
        shotsTypeMenu.addAction(actPreferencesShotsSize)
        actPreferencesShotsSize.triggered.connect(self.setShotsSize)

        layerPreferencesMenu.addMenu(shotsTypeMenu)

        # Sail line: color + size
        actPreferencesSailColor = QAction('Cor', self)
        actPreferencesSailColor.setStatusTip('Sail line color')
        sailTypeMenu.addAction(actPreferencesSailColor)
        actPreferencesSailColor.triggered.connect(self.setSailColor)

        actPreferencesSailSize = QAction('Tamanho', self)
        actPreferencesSailSize.setStatusTip('Sail line size')
        sailTypeMenu.addAction(actPreferencesSailSize)
        actPreferencesSailSize.triggered.connect(self.setSailSize)

        layerPreferencesMenu.addMenu(sailTypeMenu)

        # Nodes polygon (pol2): color + line width
        actPreferencesPolNodeColor = QAction('Cor', self)
        actPreferencesPolNodeColor.setStatusTip('Nodes polygon outline color')
        polNodesTypeMenu.addAction(actPreferencesPolNodeColor)
        actPreferencesPolNodeColor.triggered.connect(self.setPolNodeColor)

        actPreferencesPolNodeWidth = QAction('Espessura da linha', self)
        actPreferencesPolNodeWidth.setStatusTip('Nodes polygon outline width')
        polNodesTypeMenu.addAction(actPreferencesPolNodeWidth)
        actPreferencesPolNodeWidth.triggered.connect(self.setPolNodeWidth)

        layerPreferencesMenu.addMenu(polNodesTypeMenu)

        # Shots polygon (polshot): color + line width
        polShotsTypeMenu = QMenu('Shots Polygon Layer', self)

        actPreferencesPolShotColor = QAction('Cor', self)
        actPreferencesPolShotColor.setStatusTip('Shots polygon outline color')
        polShotsTypeMenu.addAction(actPreferencesPolShotColor)
        actPreferencesPolShotColor.triggered.connect(self.setPolShotColor)

        actPreferencesPolShotWidth = QAction('Espessura da linha', self)
        actPreferencesPolShotWidth.setStatusTip('Shots polygon outline width')
        polShotsTypeMenu.addAction(actPreferencesPolShotWidth)
        actPreferencesPolShotWidth.triggered.connect(self.setPolShotWidth)

        layerPreferencesMenu.addMenu(polShotsTypeMenu)

        # Fold map: transparency + color scale legend
        foldTypeMenu = QMenu('Fold Map Layer', self)

        actFoldTransparency = QAction('Transparência', self)
        actFoldTransparency.setStatusTip('Fold map transparency')
        foldTypeMenu.addAction(actFoldTransparency)
        actFoldTransparency.triggered.connect(self.setFoldTransparency)

        self.actShowFoldLegend = QAction('Mostrar escala de cores', self, checkable=True)
        self.actShowFoldLegend.setStatusTip('Show/hide fold map color legend')
        self.actShowFoldLegend.setChecked(False)
        foldTypeMenu.addAction(self.actShowFoldLegend)
        self.actShowFoldLegend.triggered.connect(self.toggleFoldLegend)

        layerPreferencesMenu.addMenu(foldTypeMenu)

        # Azimuth map: transparency + color scale legend
        azimuthTypeMenu = QMenu('Azimuth Map Layer', self)

        actAzimuthTransparency = QAction('Transparência', self)
        actAzimuthTransparency.setStatusTip('Azimuth map transparency')
        azimuthTypeMenu.addAction(actAzimuthTransparency)
        actAzimuthTransparency.triggered.connect(self.setAzimuthTransparency)

        self.actShowAzimuthLegend = QAction('Mostrar escala de cores', self, checkable=True)
        self.actShowAzimuthLegend.setStatusTip('Show/hide azimuth map color legend')
        self.actShowAzimuthLegend.setChecked(False)
        azimuthTypeMenu.addAction(self.actShowAzimuthLegend)
        self.actShowAzimuthLegend.triggered.connect(self.toggleAzimuthLegend)

        layerPreferencesMenu.addMenu(azimuthTypeMenu)

        # Preferences
        preferencesMenu = menubar.addMenu('&Preferences')
        colorAct = QAction(QIcon(":/icons/backgroundcolor.png"), 'Background color', self)
        colorAct.setShortcut('Ctrl+w')
        colorAct.setStatusTip('Background color')
        preferencesMenu.addAction(colorAct)
        colorAct.triggered.connect(self.colorDialog)

        dataDirAct = QAction('Diretorio de dados', self)
        dataDirAct.setStatusTip('Pasta padrao aberta pelos dialogos de "Open file" (Layers)')
        preferencesMenu.addAction(dataDirAct)
        dataDirAct.triggered.connect(self.setDataDir)

        # Computations
        computationsMenu = menubar.addMenu('&Computations')
        compAct = QAction(QIcon('backgroundcolor.png'), 'Total Number of Nodes', self)

        foldAct = QAction(QIcon(":/icons/polygon.png"), 'Fold Map', self)
        foldAct.setStatusTip('Compute fold map from nodes and shots positions')
        computationsMenu.addAction(foldAct)
        foldAct.triggered.connect(self.computeFoldMap)

        azimuthAct = QAction(QIcon(":/icons/polygon.png"), 'Azimuth Map', self)
        azimuthAct.setStatusTip('Compute azimuth map from nodes and shots positions')
        computationsMenu.addAction(azimuthAct)
        azimuthAct.triggered.connect(self.computeAzimuthMap)

        foldRoseAct = QAction(QIcon(":/icons/polygon.png"), 'Fold Rose (Azimute)', self)
        foldRoseAct.setStatusTip('Compute fold distribution by azimuth sector (polar diagram)')
        computationsMenu.addAction(foldRoseAct)
        foldRoseAct.triggered.connect(self.computeFoldRose)

        cmpMenu = QMenu('Arquivo CMP', self)

        buildCmpAct = QAction('Gerar arquivo CMP', self)
        buildCmpAct.setStatusTip('Compute and cache all node-shot pairs (midpoint, offset, azimuth) up to a max offset')
        cmpMenu.addAction(buildCmpAct)
        buildCmpAct.triggered.connect(self.buildCMPTable)

        saveCmpAct = QAction('Salvar arquivo CMP', self)
        saveCmpAct.setStatusTip('Save the cached CMP table to a CSV file')
        cmpMenu.addAction(saveCmpAct)
        saveCmpAct.triggered.connect(self.saveCMPTable)

        loadCmpAct = QAction('Carregar arquivo CMP', self)
        loadCmpAct.setStatusTip('Load a previously saved CMP table from a CSV file')
        cmpMenu.addAction(loadCmpAct)
        loadCmpAct.triggered.connect(self.loadCMPTable)

        computationsMenu.addMenu(cmpMenu)

        # Design
        designMenu = menubar.addMenu('&Design')

        designNodesAct = QAction(QIcon(":/icons/polygon.png"), 'Gerar Nodes (grid no Poligono)', self)
        designNodesAct.setStatusTip('Generate a regular nodes grid inside the pol2 (Node Polygon) boundary')
        designMenu.addAction(designNodesAct)
        designNodesAct.triggered.connect(self.designNodesGrid)

        designShotsAct = QAction(QIcon(":/icons/polygon.png"), 'Gerar Shots (grid no Poligono)', self)
        designShotsAct.setStatusTip('Generate a regular shots grid inside the polshot (Shot Polygon) boundary')
        designMenu.addAction(designShotsAct)
        designShotsAct.triggered.connect(self.designShotsGrid)

        # Help
        helpMenu = menubar.addMenu('&Help')
        helpAct = QAction(QIcon(":/icons/info.png"), 'Manual / Ajuda', self)
        helpAct.setStatusTip('Ver o manual de uso do programa')
        helpMenu.addAction(helpAct)
        helpAct.triggered.connect(self.showHelp)

        aboutAct = QAction(QIcon(":/icons/info.png"), 'Sobre', self)
        aboutAct.setStatusTip('Sobre este programa')
        helpMenu.addAction(aboutAct)
        aboutAct.triggered.connect(self.showAbout)

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

        # Select area (count nodes/shots)
        self.area_select_action = QAction(QIcon(":/icons/polygon.png"), "Select Area", self)
        self.area_select_action.setCheckable(True)
        self.area_select_action.setStatusTip('Arraste um retangulo no mapa para contar nodes/shots na area')
        self.toolbar.addAction(self.area_select_action)
        self.area_select_action.triggered.connect(self.selectArea)
        self.tool_area_select = RectSelectTool(self.map_canvas)
        self.tool_area_select.area_selected.connect(self.countInArea)

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

    def replaceLayerInLay(self, name, new_layer):
        """ Remove any existing layer(s) named `name` from the global `lay`
        list (and from the project, if already registered) before appending
        the freshly loaded one. Without this, a stale/invalid layer with the
        same name (e.g. from the startup auto-load) can shadow the new one,
        since lookups always take the first match by name. """
        existing = [x for x in lay if x.name() == name]
        for old in existing:
            lay.remove(old)
            try:
                self.project.instance().removeMapLayer(old.id())
            except Exception:
                pass
        lay.append(new_layer)

        if name in ('nodes', 'shots'):
            # the CMP cache (fold/azimuth/rose) was computed from the
            # previous nodes/shots geometry -- it's now stale, so drop it
            # rather than silently reusing wrong results
            self.cmp_file = None
            self.cmp_max_offset = None
            self.cmp_extent = None

    def toPolygonLayer(self, point_layer, name):
        """ Build a single closed polygon from an ordered set of vertex points
        (e.g. loaded from a txt file). If the layer given is already a polygon
        layer (e.g. loaded from a polygon shapefile via ogr), return it as-is. """

        if not point_layer or not point_layer.isValid():
            return None

        if point_layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            return point_layer

        pts = [f.geometry().asPoint() for f in point_layer.getFeatures()
              if f.geometry() and not f.geometry().isEmpty()]
        if len(pts) < 3:
            return None
        if pts[0] != pts[-1]:
            pts.append(pts[0])

        poly_layer = QgsVectorLayer("Polygon?crs=epsg:31983", name, "memory")
        prov = poly_layer.dataProvider()
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolygonXY([pts]))
        prov.addFeatures([feat])
        poly_layer.updateExtents()
        return poly_layer

    def showVisibleMapLayers(self):
     lay1=[]
     self.project.instance().addMapLayers(lay)

     if (next((x for x in lay if x.name() == 'nodes'), None)):
       layer=next((x for x in lay if x.name() == 'nodes'), None)
       if self.actShowNodesLayer.isChecked():
         isymbol = QgsMarkerSymbol.createSimple({'color' : self.nodesColor.name(),
                  'size' : str(self.nodesSize), 'name' : "circle" })
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
         isymbol = QgsMarkerSymbol.createSimple({'color' : self.shotsColor.name(),
                  'size' : str(self.shotsSize), 'name' : "star" })
         renderer = QgsSingleSymbolRenderer(isymbol)
         layer.setRenderer(renderer)
         lay1.append(layer)

     else:
       if self.actShowShotsLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Shots shapefile NOT loaded")
         self.actShowShotsLayer.setChecked(False)


#PORRA99999
     if (next((x for x in lay if x.name() == 'sail'), None)):
       layer=next((x for x in lay if x.name() == 'sail'), None)
       if self.actShowSailLayer.isChecked():
          isymbol = QgsMarkerSymbol.createSimple({'color' : self.sailColor.name(),
                  'size' : str(self.sailSize), 'name' : "square" })
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
                  'size' : ".5", 'name' : "circle" })
          renderer = QgsSingleSymbolRenderer(isymbol)
          layer.setRenderer(renderer)
          lay1.append(layer)
     else:
       if self.actShowGridLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Grid shapefile NOT loaded")
         self.actShowGridLayer.setChecked(False)






     if (next((x for x in lay if x.name() == 'pol2'), None)):
       layer=next((x for x in lay if x.name() == 'pol2'), None)
       if self.actShowPolNodeLayer.isChecked():
         fill_color = QColor(self.polNodeColor.red(), self.polNodeColor.green(),
                     self.polNodeColor.blue(), 60)
         symbol_layer = QgsSimpleFillSymbolLayer()
         symbol_layer.setColor(fill_color)
         symbol_layer.setStrokeColor(self.polNodeColor)
         symbol_layer.setStrokeWidth(self.polNodeOutlineWidth)
         isymbol = QgsFillSymbol()
         isymbol.changeSymbolLayer(0, symbol_layer)
         renderer = QgsSingleSymbolRenderer(isymbol)
         layer.setRenderer(renderer)
         layer.triggerRepaint()
         lay1.append(layer)
     else:
       if self.actShowPolNodeLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Pol2 shapefile NOT loaded")
         self.actShowPolNodeLayer.setChecked(False)

     if (next((x for x in lay if x.name() == 'polshot'), None)):
       layer=next((x for x in lay if x.name() == 'polshot'), None)
       if self.actShowPolShotLayer.isChecked():
        fill_color = QColor(self.polShotColor.red(), self.polShotColor.green(),
                    self.polShotColor.blue(), 60)
        symbol_layer = QgsSimpleFillSymbolLayer()
        symbol_layer.setColor(fill_color)
        symbol_layer.setStrokeColor(self.polShotColor)
        symbol_layer.setStrokeWidth(self.polShotOutlineWidth)
        isymbol = QgsFillSymbol()
        isymbol.changeSymbolLayer(0, symbol_layer)
        renderer = QgsSingleSymbolRenderer(isymbol)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
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

     # Fold map (computed layer)
     if (next((x for x in lay if x.name() == 'fold_map'), None)):
       layer=next((x for x in lay if x.name() == 'fold_map'), None)
       if self.actShowFoldLayer.isChecked():
         self.applyFoldRenderer(layer)
         lay1.append(layer)
     else:
       if self.actShowFoldLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Fold map NOT computed yet")
         self.actShowFoldLayer.setChecked(False)

     # Azimuth map (computed layer)
     if (next((x for x in lay if x.name() == 'azimuth_map'), None)):
       layer=next((x for x in lay if x.name() == 'azimuth_map'), None)
       if self.actShowAzimuthLayer.isChecked():
         self.applyAzimuthRenderer(layer)
         lay1.append(layer)
     else:
       if self.actShowAzimuthLayer.isChecked():
         QMessageBox.about(self, "LAYER LOADED!", "Azimuth map NOT computed yet")
         self.actShowAzimuthLayer.setChecked(False)

     self.project.instance().addMapLayers(lay1)
     self.map_canvas.setLayers(lay1)


     self.map_canvas.zoomToFullExtent()
###
    def ogrNodesInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if path[0]:
           (name, ext) = os.path.basename(path[0]).split('.')
           layer = QgsVectorLayer(path[0], 'nodes', 'ogr')
           if layer.isValid():
             self.replaceLayerInLay('nodes', layer)
             self.actShowNodesLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED", "Nodes shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Nodes shapefile NOT loaded")
 
    def ogrShotsInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'shots', 'ogr')
           if layer.isValid():
             self.replaceLayerInLay('shots', layer)
             self.actShowShotsLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Shots shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Shot shapefile NOT loaded")

    def ogrSailInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'sail', 'ogr')
           if layer.isValid():
             self.replaceLayerInLay('sail', layer)
             self.actShowSailLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Sail shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Sail shapefile NOT loaded")

    def ogrGridInput(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if path[0]:
           layer = QgsVectorLayer(path[0], 'grid', 'ogr')
           if layer.isValid():
             self.replaceLayerInLay('grid', layer)
             self.actShowGridLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Grid shapefile loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Grid shapefile NOT loaded")





    def ogrPol2Input(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if path[0]:
           raw_layer = QgsVectorLayer(path[0], 'pol2', 'ogr')
           if raw_layer.isValid():
             poly_layer = self.toPolygonLayer(raw_layer, 'pol2')
             if poly_layer:
               self.replaceLayerInLay('pol2', poly_layer)
               self.actShowPolNodeLayer.setChecked(True)
               self.showVisibleMapLayers()
               ext = poly_layer.extent()
               QMessageBox.about(self, "LAYER LOADED!",
                   "Pol2 shapefile loaded\nVertices (entrada): {}\nExtensao X: [{:.1f}, {:.1f}]  Y: [{:.1f}, {:.1f}]".format(
                       raw_layer.featureCount(),
                       ext.xMinimum(), ext.xMaximum(), ext.yMinimum(), ext.yMaximum()))
             else:
               QMessageBox.about(self, "LAYER NOT LOADED",
                   "Pol2: menos de 3 pontos validos, nao foi possivel montar o poligono")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Pol2 shapefile NOT loaded")

    def ogrPol3Input(self):
        path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if path[0]:
           raw_layer = QgsVectorLayer(path[0], 'polshot', 'ogr')
           if raw_layer.isValid():
             poly_layer = self.toPolygonLayer(raw_layer, 'polshot')
             if poly_layer:
               self.replaceLayerInLay('polshot', poly_layer)
               self.actShowPolShotLayer.setChecked(True)
               self.showVisibleMapLayers()
               ext = poly_layer.extent()
               QMessageBox.about(self, "LAYER LOADED!",
                   "Polshot shapefile loaded\nVertices (entrada): {}\nExtensao X: [{:.1f}, {:.1f}]  Y: [{:.1f}, {:.1f}]".format(
                       raw_layer.featureCount(),
                       ext.xMinimum(), ext.xMaximum(), ext.yMinimum(), ext.yMaximum()))
             else:
               QMessageBox.about(self, "LAYER NOT LOADED",
                   "Polshot: menos de 3 pontos validos, nao foi possivel montar o poligono")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Polshot shapefile NOT loaded")

    def txtNodesInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
       if path[0]:
         filename = "file://"+path[0]
         uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
         layer = QgsVectorLayer(uri, "nodes", "delimitedtext")
         if layer.isValid():
             self.replaceLayerInLay('nodes', layer)
             self.actShowNodesLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Nodes txt layer  loaded")
         else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Nodes txt-delimited NOT loaded")

    def txtShotsInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "shots", "delimitedtext")
           if layer.isValid():
             self.replaceLayerInLay('shots', layer)
             self.actShowShotsLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Shots txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Shots txt-delimited NOT loaded")

    def txtSailInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "sail", "delimitedtext")
           if layer.isValid():
             self.replaceLayerInLay('sail', layer)
             self.actShowSailLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Sail txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Sail txt-delimited NOT loaded")

    def txtGridInput(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           layer = QgsVectorLayer(uri, "grid", "delimitedtext")
           if layer.isValid():
             self.replaceLayerInLay('grid', layer)
             self.actShowGridLayer.setChecked(True)
             self.showVisibleMapLayers()
             QMessageBox.about(self, "LAYER LOADED!", "Grid txt layer  loaded")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Grid txt-delimited NOT loaded")




    def txtPol2Input(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           raw_layer = QgsVectorLayer(uri, "pol2", "delimitedtext")
           if raw_layer.isValid():
             poly_layer = self.toPolygonLayer(raw_layer, 'pol2')
             if poly_layer:
               self.replaceLayerInLay('pol2', poly_layer)
               self.actShowPolNodeLayer.setChecked(True)
               self.showVisibleMapLayers()
               ext = poly_layer.extent()
               QMessageBox.about(self, "LAYER LOADED!",
                   "Pol2 txt layer loaded\nVertices (entrada): {}\nExtensao X: [{:.1f}, {:.1f}]  Y: [{:.1f}, {:.1f}]".format(
                       raw_layer.featureCount(),
                       ext.xMinimum(), ext.xMaximum(), ext.yMinimum(), ext.yMaximum()))
             else:
               QMessageBox.about(self, "LAYER NOT LOADED",
                   "Pol2: menos de 3 pontos validos, nao foi possivel montar o poligono")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Pol2 txt-delimited NOT loaded")

    def txtPol3Input(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
       if path[0]:
           filename = "file://"+path[0]   
           uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
           raw_layer = QgsVectorLayer(uri, "polshot", "delimitedtext")
           if raw_layer.isValid():
             poly_layer = self.toPolygonLayer(raw_layer, 'polshot')
             if poly_layer:
               self.replaceLayerInLay('polshot', poly_layer)
               self.actShowPolShotLayer.setChecked(True)
               self.showVisibleMapLayers()
               ext = poly_layer.extent()
               QMessageBox.about(self, "LAYER LOADED!",
                   "Polshot txt layer loaded\nVertices (entrada): {}\nExtensao X: [{:.1f}, {:.1f}]  Y: [{:.1f}, {:.1f}]".format(
                       raw_layer.featureCount(),
                       ext.xMinimum(), ext.xMaximum(), ext.yMinimum(), ext.yMaximum()))
             else:
               QMessageBox.about(self, "LAYER NOT LOADED",
                   "Polshot: menos de 3 pontos validos, nao foi possivel montar o poligono")
           else:
             QMessageBox.about(self, "LAYER NOT LOADED", "Polshot txt-delimited NOT loaded")

    def rasterBathymetry(self):
       path = QFileDialog.getOpenFileName(self, 'Open file', self.data_dir, options=QFileDialog.DontUseNativeDialog)
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

    def _readCMPHeader(self, path):
        """ Read just the metadata header of a CMP cache file (binary
        format): returns (extent, max_offset, count) where extent is
        (xmin,xmax,ymin,ymax) or None, max_offset is a float or None, and
        count is the number of pair records in the file (computed from
        the file size -- no need to scan the records). Returns
        (None, None, 0) on any read error or if the file isn't a
        recognized CMP cache file. """
        try:
            with open(path, 'rb') as f:
                magic = f.read(len(CMP_MAGIC))
                if magic != CMP_MAGIC:
                    return None, None, 0
                header_bytes = f.read(CMP_HEADER_SIZE)
                if len(header_bytes) < CMP_HEADER_SIZE:
                    return None, None, 0
                xmin, xmax, ymin, ymax, max_offset = struct.unpack(CMP_HEADER_FMT, header_bytes)
            total_size = os.path.getsize(path)
            data_size = total_size - len(CMP_MAGIC) - CMP_HEADER_SIZE
            count = max(0, data_size // CMP_RECORD_SIZE)
            return (xmin, xmax, ymin, ymax), max_offset, count
        except Exception:
            return None, None, 0

    def _tryAutoLoadCMPCache(self, notify=False):
        """ If <data_dir>/cmp_cache.cmp exists, adopt it as the current CMP
        cache (self.cmp_file/self.cmp_max_offset/self.cmp_extent) so it is
        reused instead of silently ignored -- this is what lets the cache
        survive across app restarts, since only the in-memory reference
        (not the file itself) is lost when the app closes. """
        candidate = os.path.join(self.data_dir, "cmp_cache.cmp")
        if not os.path.exists(candidate):
            return False

        extent, max_offset_cap, count = self._readCMPHeader(candidate)
        if count == 0 or max_offset_cap is None:
            return False

        self.cmp_file = candidate
        self.cmp_extent = extent
        self.cmp_max_offset = max_offset_cap

        if notify:
            QMessageBox.information(self, "Arquivo CMP",
                "Cache CMP encontrado e carregado automaticamente:\n%s\n\n"
                "%d pares, offset maximo = %.1f m"
                % (candidate, count, max_offset_cap))
        return True

    def setDataDir(self):
        new_dir = QFileDialog.getExistingDirectory(self,
            "Escolha a pasta com seus arquivos (nodes, shots, sail, etc.)",
            self.data_dir, options=QFileDialog.DontUseNativeDialog)
        if new_dir:
            self.data_dir = new_dir
            self._tryAutoLoadCMPCache(notify=True)

    def showHelp(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajuda - OBN Design")
        dialog.resize(700, 600)
        layout = QVBoxLayout(dialog)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(HELP_HTML)
        layout.addWidget(text)

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def showAbout(self):
        QMessageBox.about(self, "Sobre o OBN Design",
            "<h3>OBN Design</h3>"
            "<p>Versao %s</p>"
            "<p>Desenvolvido no ambito do projeto <b>%s</b>.</p>"
            "<p>Ferramenta para desenho e QC de aquisicao sismica OBN "
            "(Ocean Bottom Node): plotagem de nodes, shots, sail lines e "
            "poligonos de area; geracao de grid de nodes/shots; calculo de "
            "fold, azimute e diagramas offset-azimute.</p>"
            % (APP_VERSION, APP_PROJECT))

    def colorLayerDialog(self):

        col= QColorDialog.getColor()
        if col.isValid():
           isymbol = QgsMarkerSymbolV2.createSimple({'color' : col,
                  'size' : "5", 'name' : "circle" })
           renderer = QgsSingleSymbolRendererV2(isymbol)
           self.layer.setRendererV2(renderer)

    def setNodesColor(self):
        col = QColorDialog.getColor(self.nodesColor, self, "Cor dos Nodes")
        if col.isValid():
            self.nodesColor = col
            self.showVisibleMapLayers()

    def setNodesSize(self):
        size, ok = QInputDialog.getDouble(self, "Tamanho dos Nodes",
            "Tamanho:", self.nodesSize, 0.1, 50.0, 1)
        if ok:
            self.nodesSize = size
            self.showVisibleMapLayers()

    def setShotsColor(self):
        col = QColorDialog.getColor(self.shotsColor, self, "Cor dos Shots")
        if col.isValid():
            self.shotsColor = col
            self.showVisibleMapLayers()

    def setShotsSize(self):
        size, ok = QInputDialog.getDouble(self, "Tamanho dos Shots",
            "Tamanho:", self.shotsSize, 0.1, 50.0, 1)
        if ok:
            self.shotsSize = size
            self.showVisibleMapLayers()

    def setSailColor(self):
        col = QColorDialog.getColor(self.sailColor, self, "Cor da Sail Line")
        if col.isValid():
            self.sailColor = col
            self.showVisibleMapLayers()

    def setSailSize(self):
        size, ok = QInputDialog.getDouble(self, "Tamanho da Sail Line",
            "Tamanho:", self.sailSize, 0.1, 50.0, 1)
        if ok:
            self.sailSize = size
            self.showVisibleMapLayers()

    def setPolNodeColor(self):
        col = QColorDialog.getColor(self.polNodeColor, self, "Cor do Poligono de Nodes")
        if col.isValid():
            self.polNodeColor = col
            self.showVisibleMapLayers()

    def setPolNodeWidth(self):
        width, ok = QInputDialog.getDouble(self, "Espessura da linha - Poligono de Nodes",
            "Espessura (mm):", self.polNodeOutlineWidth, 0.1, 20.0, 2)
        if ok:
            self.polNodeOutlineWidth = width
            self.showVisibleMapLayers()

    def setPolShotColor(self):
        col = QColorDialog.getColor(self.polShotColor, self, "Cor do Poligono de Shots")
        if col.isValid():
            self.polShotColor = col
            self.showVisibleMapLayers()

    def setPolShotWidth(self):
        width, ok = QInputDialog.getDouble(self, "Espessura da linha - Poligono de Shots",
            "Espessura (mm):", self.polShotOutlineWidth, 0.1, 20.0, 2)
        if ok:
            self.polShotOutlineWidth = width
            self.showVisibleMapLayers()

    def showXY( self, p ):
       """ SLOT. Show coordinates """
       self.lblXY.setText( str(float(p.x())) + " | " + str(float(p.y())) )

    def connect_pt(self):
        self.map_canvas.setMapTool(self.tool_connect)
        self.connect_action.setChecked(True)

    def selectArea(self):
        self.map_canvas.setMapTool(self.tool_area_select)
        self.area_select_action.setChecked(True)

    def countInArea(self, rect):
        nodes_layer = next((x for x in lay if x.name() == 'nodes'), None)
        shots_layer = next((x for x in lay if x.name() == 'shots'), None)

        node_count = 0
        shot_count = 0

        if nodes_layer and nodes_layer.isValid():
            for f in nodes_layer.getFeatures():
                geom = f.geometry()
                if geom and not geom.isEmpty() and rect.contains(geom.asPoint()):
                    node_count += 1

        if shots_layer and shots_layer.isValid():
            for f in shots_layer.getFeatures():
                geom = f.geometry()
                if geom and not geom.isEmpty() and rect.contains(geom.asPoint()):
                    shot_count += 1

        QMessageBox.information(self, "Contagem na Area",
            "Area selecionada:\nX: [%.1f, %.1f]   Y: [%.1f, %.1f]\n\nNodes: %d\nShots: %d"
            % (rect.xMinimum(), rect.xMaximum(), rect.yMinimum(), rect.yMaximum(),
               node_count, shot_count))

        self.area_select_action.setChecked(False)

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

    def getSourceReceiverPairs(self, min_offset, max_offset, progress_title="Calculando...", cache_path=None):
        """ Generator yielding (mx, my, offset, azimuth) tuples for every
        node-shot pair with min_offset <= offset <= max_offset.

        Memory-safe for very large surveys: pairs are streamed one at a
        time, never all held in memory at once, and the on-disk cache is
        a compact binary format (fast to read/write, no text parsing).

        - If an on-disk CMP cache (self.cmp_file) already covers
          max_offset, pairs are streamed back from that file (filtered by
          offset), without touching the nodes/shots layers again.
        - Otherwise, pairs are computed fresh from the nodes/shots layers
          (via a spatial index) and, in the same pass, streamed straight
          to a new CMP cache file on disk (cache_path, defaulting to
          <data_dir>/cmp_cache.cmp) -- so every Fold/Azimuth/Rose
          calculation doubles as "Gerar arquivo CMP" automatically.

        After exhausting the generator, check self.pairs_error (a message
        string, or None), self.pairs_canceled (bool) and
        self.pairs_from_cache (bool) to know the outcome. """

        self.pairs_error = None
        self.pairs_canceled = False
        self.pairs_from_cache = False

        if (self.cmp_file and self.cmp_max_offset is not None
                and max_offset <= self.cmp_max_offset
                and os.path.exists(self.cmp_file)):
            self.pairs_from_cache = True
            try:
                with open(self.cmp_file, 'rb') as f:
                    magic = f.read(len(CMP_MAGIC))
                    if magic != CMP_MAGIC:
                        raise ValueError("formato de arquivo CMP invalido ou incompativel")
                    f.read(CMP_HEADER_SIZE)   # already known via self.cmp_extent/self.cmp_max_offset
                    while True:
                        chunk = f.read(CMP_RECORD_SIZE)
                        if len(chunk) < CMP_RECORD_SIZE:
                            break
                        mx, my, offset, azimuth = struct.unpack(CMP_RECORD_FMT, chunk)
                        if min_offset <= offset <= max_offset:
                            yield (mx, my, offset, azimuth)
            except Exception as e:
                self.pairs_error = "Erro ao ler o cache CMP (%s): %s" % (self.cmp_file, str(e))
            return

        nodes_layer = next((x for x in lay if x.name() == 'nodes'), None)
        shots_layer = next((x for x in lay if x.name() == 'shots'), None)

        if not nodes_layer or not shots_layer:
            self.pairs_error = "Carregue as camadas de Nodes e Shots antes de calcular."
            return
        if not nodes_layer.isValid() or not shots_layer.isValid():
            self.pairs_error = "As camadas de Nodes e/ou Shots nao sao validas."
            return

        node_pts = [f.geometry().asPoint() for f in nodes_layer.getFeatures()
                   if f.geometry() and not f.geometry().isEmpty()]
        shot_pts = [f.geometry().asPoint() for f in shots_layer.getFeatures()
                   if f.geometry() and not f.geometry().isEmpty()]

        if not node_pts or not shot_pts:
            self.pairs_error = "As camadas de Nodes/Shots estao vazias."
            return

        index = QgsSpatialIndex()
        node_feats = []
        for i, p in enumerate(node_pts):
            feat = QgsFeature(i)
            feat.setGeometry(QgsGeometry.fromPointXY(p))
            node_feats.append(feat)
            index.insertFeature(feat)

        all_x = [p.x() for p in node_pts] + [p.x() for p in shot_pts]
        all_y = [p.y() for p in node_pts] + [p.y() for p in shot_pts]
        self.cmp_extent = (min(all_x), max(all_x), min(all_y), max(all_y))

        if cache_path is None:
            cache_path = os.path.join(self.data_dir, "cmp_cache.cmp")

        cache_f = None
        try:
            cache_f = open(cache_path, 'wb')
            cache_f.write(CMP_MAGIC)
            cache_f.write(struct.pack(CMP_HEADER_FMT,
                self.cmp_extent[0], self.cmp_extent[1],
                self.cmp_extent[2], self.cmp_extent[3], max_offset))
        except Exception:
            cache_f = None   # if the cache file can't be written, still compute normally

        progress = QProgressDialog(progress_title, "Cancelar", 0, len(shot_pts), self)
        progress.setWindowTitle("Calculando")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        try:
            for i, sp in enumerate(shot_pts):
                if i % 20 == 0:
                    progress.setValue(i)
                    if progress.wasCanceled():
                        self.pairs_canceled = True
                        break
                rect = QgsRectangle(sp.x() - max_offset, sp.y() - max_offset,
                                    sp.x() + max_offset, sp.y() + max_offset)
                for nid in index.intersects(rect):
                    np_ = node_pts[nid]
                    dx = np_.x() - sp.x()
                    dy = np_.y() - sp.y()
                    offset = math.hypot(dx, dy)
                    if offset > max_offset or offset < min_offset:
                        continue
                    mx = (sp.x() + np_.x()) / 2.0
                    my = (sp.y() + np_.y()) / 2.0
                    azimuth = math.degrees(math.atan2(dx, dy))
                    if azimuth < 0:
                        azimuth += 360.0
                    if cache_f:
                        cache_f.write(struct.pack(CMP_RECORD_FMT, mx, my, offset, azimuth))
                    yield (mx, my, offset, azimuth)
            progress.setValue(len(shot_pts))
        finally:
            if cache_f:
                cache_f.close()
                if not self.pairs_canceled and not self.pairs_error:
                    self.cmp_file = cache_path
                    self.cmp_max_offset = max_offset
                else:
                    try:
                        os.remove(cache_path)
                    except OSError:
                        pass

    def buildCMPTable(self):
        """ Compute ALL node-shot pairs (mx, my, offset, azimuth) up to a
        chosen max offset, streaming them straight to a CSV file on disk
        (never holding the full set in memory). Any Fold/Azimuth/Rose
        calculation done afterwards with max offset <= this cap reuses the
        file instead of recomputing the full spatial search. """

        max_offset, ok = QInputDialog.getDouble(self, "Arquivo CMP",
            "Offset maximo a incluir no arquivo CMP (m):\n"
            "Calculos feitos depois podem usar qualquer offset ate este valor\n"
            "sem precisar recalcular tudo de novo.",
            8000.0, 0.0, 1000000.0, 1)
        if not ok:
            return

        default_path = os.path.join(self.data_dir, "cmp_cache.cmp")
        path, _ = QFileDialog.getSaveFileName(self, "Salvar arquivo CMP", default_path,
            "Arquivo CMP (*.cmp)", options=QFileDialog.DontUseNativeDialog)
        if not path:
            return
        if not path.lower().endswith('.cmp'):
            path += '.cmp'

        old_file, old_cap = self.cmp_file, self.cmp_max_offset
        self.cmp_file, self.cmp_max_offset = None, None   # force a fresh computation

        count = 0
        for _ in self.getSourceReceiverPairs(0.0, max_offset, "Gerando arquivo CMP...", cache_path=path):
            count += 1

        if self.pairs_error:
            self.cmp_file, self.cmp_max_offset = old_file, old_cap
            QMessageBox.warning(self, "Arquivo CMP", self.pairs_error)
            return
        if self.pairs_canceled:
            self.cmp_file, self.cmp_max_offset = old_file, old_cap
            QMessageBox.information(self, "Arquivo CMP", "Geracao cancelada.")
            return
        if count == 0:
            self.cmp_file, self.cmp_max_offset = old_file, old_cap
            QMessageBox.information(self, "Arquivo CMP",
                "Nenhum par fonte-receptor encontrado ate o offset informado.")
            return

        QMessageBox.information(self, "Arquivo CMP",
            "Arquivo CMP gerado e salvo em disco:\n%s\n\n"
            "%d pares (offset ate %.1f m).\n\n"
            "Fold Map, Azimuth Map e Fold Rose calculados agora com offset\n"
            "maximo ate esse valor vao reaproveitar o arquivo automaticamente."
            % (path, count, max_offset))

    def saveCMPTable(self):
        """ Save a copy of the current on-disk CMP cache elsewhere. """
        if not self.cmp_file or not os.path.exists(self.cmp_file):
            QMessageBox.warning(self, "Arquivo CMP",
                "Nenhum arquivo CMP em cache no momento. Calcule um Fold/Azimuth Map, "
                "ou use 'Gerar arquivo CMP' primeiro.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Salvar copia do arquivo CMP",
            self.data_dir, "Arquivo CMP (*.cmp)", options=QFileDialog.DontUseNativeDialog)
        if not path:
            return
        if not path.lower().endswith('.cmp'):
            path += '.cmp'

        try:
            shutil.copy(self.cmp_file, path)
        except Exception as e:
            QMessageBox.warning(self, "Arquivo CMP", "Erro ao copiar: %s" % str(e))
            return

        QMessageBox.information(self, "Arquivo CMP", "Copia salva em:\n%s" % path)

    def loadCMPTable(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carregar arquivo CMP", self.data_dir,
            "Arquivo CMP (*.cmp)", options=QFileDialog.DontUseNativeDialog)
        if not path:
            return

        extent, max_offset_cap, count = self._readCMPHeader(path)

        if count == 0:
            QMessageBox.warning(self, "Arquivo CMP", "Arquivo vazio ou invalido.")
            return

        self.cmp_file = path
        self.cmp_extent = extent
        self.cmp_max_offset = max_offset_cap

        if self.cmp_max_offset is None:
            max_offset_cap, ok = QInputDialog.getDouble(self, "Arquivo CMP",
                "O arquivo nao tem cabecalho de offset maximo.\n"
                "Informe o offset maximo coberto por este arquivo (m):",
                8000.0, 0.0, 1000000.0, 1)
            if ok:
                self.cmp_max_offset = max_offset_cap

        QMessageBox.information(self, "Arquivo CMP",
            "Arquivo CMP carregado (%s): %d pares, offset maximo = %s m"
            % (path, count, str(self.cmp_max_offset)))

    def _designGridInPolygon(self, poly_name, layer_name, title):
        """ Generate a regular point grid (spacing dx along the line, dy
        between lines, at a given azimuth) clipped to the given polygon
        layer (poly_name), and save/load it as a <layer_name>.txt file.
        Shared by Design > Gerar Nodes and Design > Gerar Shots. """

        pol_layer = next((x for x in lay if x.name() == poly_name), None)
        if not pol_layer or not pol_layer.isValid():
            QMessageBox.warning(self, title,
                "Carregue o poligono de %s (%s) antes de gerar o grid." % (layer_name, poly_name))
            return

        feats = list(pol_layer.getFeatures())
        if not feats or not feats[0].geometry() or feats[0].geometry().isEmpty():
            QMessageBox.warning(self, title,
                "O poligono de %s (%s) esta vazio ou invalido." % (layer_name, poly_name))
            return
        poly_geom = feats[0].geometry()

        dx, ok1 = QInputDialog.getDouble(self, title,
            "Espacamento entre %s na linha - eixo X (m):" % layer_name, 400.0, 0.1, 100000.0, 1)
        if not ok1:
            return

        dy, ok2 = QInputDialog.getDouble(self, title,
            "Espacamento entre linhas de %s - eixo Y (m):" % layer_name, 400.0, 0.1, 100000.0, 1)
        if not ok2:
            return

        azimuth, ok3 = QInputDialog.getDouble(self, title,
            "Direcao das linhas de %s (azimute, graus, 0 = Norte):" % layer_name,
            0.0, 0.0, 359.9, 1)
        if not ok3:
            return

        start_line, ok4 = QInputDialog.getInt(self, title,
            "Numero da primeira linha (L):", 1, 1, 999999, 1)
        if not ok4:
            return

        start_station, ok5 = QInputDialog.getInt(self, title,
            "Numero da primeira estacao (S):", 1, 1, 999999, 1)
        if not ok5:
            return

        include_boundary = QMessageBox.question(self, title,
            "Incluir %s que caem exatamente em cima da linha do poligono?" % layer_name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes

        stagger = QMessageBox.question(self, title,
            "Alternar (escalonar) os %s entre uma linha e outra?\n"
            "Linhas pares deslocadas em metade do espacamento (dx/2)." % layer_name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

        theta = math.radians(azimuth)
        u = (math.sin(theta), math.cos(theta))     # along the line (station direction, spaced by dx)
        v = (math.cos(theta), -math.sin(theta))    # perpendicular (line direction, spaced by dy)

        verts = list(poly_geom.vertices())
        if not verts:
            QMessageBox.warning(self, title, "Nao foi possivel ler os vertices do poligono.")
            return

        bbox = poly_geom.boundingBox()
        cx = (bbox.xMinimum() + bbox.xMaximum()) / 2.0
        cy = (bbox.yMinimum() + bbox.yMaximum()) / 2.0

        s_vals = []
        l_vals = []
        for pt in verts:
            rx = pt.x() - cx
            ry = pt.y() - cy
            s_vals.append(rx * u[0] + ry * u[1])
            l_vals.append(rx * v[0] + ry * v[1])

        s_min, s_max = min(s_vals), max(s_vals)
        l_min, l_max = min(l_vals), max(l_vals)

        l0 = math.floor(l_min / dy) * dy
        s0 = math.floor(s_min / dx) * dx
        n_lines = int(math.floor((l_max - l0) / dy)) + 2
        n_stations = int(math.floor((s_max - s0) / dx)) + 2

        total_candidates = n_lines * n_stations
        if total_candidates > 500000:
            reply = QMessageBox.question(self, title,
                "Essa configuracao vai testar aproximadamente %d pontos candidatos, "
                "o que pode demorar bastante. Deseja continuar?" % total_candidates,
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        progress = QProgressDialog("Gerando grid de %s..." % layer_name, "Cancelar", 0, n_lines, self)
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        rows = []
        line_num = start_line
        canceled = False
        for li in range(n_lines):
            progress.setValue(li)
            if progress.wasCanceled():
                canceled = True
                break
            l_coord = l0 + li * dy
            if l_coord > l_max + dy:
                break
            s_offset = (dx / 2.0) if (stagger and li % 2 == 1) else 0.0
            station_num = start_station
            any_in_line = False
            for si in range(n_stations):
                s_coord = s0 + s_offset + si * dx
                if s_coord > s_max + dx:
                    break
                x = cx + s_coord * u[0] + l_coord * v[0]
                y = cy + s_coord * u[1] + l_coord * v[1]
                pt_geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                is_inside = poly_geom.intersects(pt_geom) if include_boundary else poly_geom.contains(pt_geom)
                if is_inside:
                    rows.append((x, y, station_num, line_num))
                    station_num += 1
                    any_in_line = True
            if any_in_line:
                line_num += 1
        progress.setValue(n_lines)

        if canceled:
            QMessageBox.information(self, title, "Geracao cancelada.")
            return

        if not rows:
            QMessageBox.information(self, title,
                "Nenhum ponto caiu dentro do poligono com esses parametros.")
            return

        default_path = os.path.join(self.data_dir, "%s_design.txt" % layer_name)
        path, _ = QFileDialog.getSaveFileName(self, "Salvar %s.txt gerado" % layer_name,
            default_path, "Text Files (*.txt)", options=QFileDialog.DontUseNativeDialog)
        if not path:
            return
        if not path.lower().endswith('.txt'):
            path += '.txt'

        try:
            with open(path, 'w') as f:
                f.write("x y s l\n")
                for x, y, s, l in rows:
                    f.write("%.2f %.2f %d %d\n" % (x, y, s, l))
        except Exception as e:
            QMessageBox.warning(self, title, "Erro ao salvar: %s" % str(e))
            return

        filename = "file://" + path
        uri = filename + "?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        new_layer = QgsVectorLayer(uri, layer_name, "delimitedtext")
        if not new_layer.isValid():
            QMessageBox.warning(self, title,
                "%s gerados e salvos em:\n%s\n\nmas nao foi possivel carregar automaticamente."
                % (layer_name.capitalize(), path))
            return

        self.replaceLayerInLay(layer_name, new_layer)
        view_checkbox = self.actShowNodesLayer if layer_name == 'nodes' else self.actShowShotsLayer
        view_checkbox.setChecked(True)
        self.showVisibleMapLayers()

        QMessageBox.information(self, title,
            "Grid de %s gerado: %d pontos em %d linhas, dentro do poligono.\n\nSalvo em:\n%s"
            % (layer_name, len(rows), line_num - start_line, path))

    def designNodesGrid(self):
        self._designGridInPolygon('pol2', 'nodes', 'Design Nodes')

    def designShotsGrid(self):
        self._designGridInPolygon('polshot', 'shots', 'Design Shots')

    def computeFoldMap(self):
        """ Compute a fold map (CMP bin coverage) from the 'nodes' (receivers)
        and 'shots' (sources) layers, and display it as a colored grid. """

        bin_size, ok1 = QInputDialog.getDouble(self, "Fold Map",
            "Tamanho do bin (m):", 100.0, 1.0, 100000.0, 1)
        if not ok1:
            return

        min_offset, ok2 = QInputDialog.getDouble(self, "Fold Map",
            "Offset minimo (m):", 0.0, 0.0, 1000000.0, 1)
        if not ok2:
            return

        max_offset, ok3 = QInputDialog.getDouble(self, "Fold Map",
            "Offset maximo (m):", 6000.0, 0.0, 1000000.0, 1)
        if not ok3:
            return

        if min_offset >= max_offset:
            QMessageBox.warning(self, "Fold Map",
                "Offset minimo deve ser menor que o offset maximo.")
            return

        xmin = ymin = None
        fold_grid = {}   # (col, row) -> fold count
        for mx, my, offset, azimuth in self.getSourceReceiverPairs(
                min_offset, max_offset, "Calculando fold map..."):
            if xmin is None:
                if self.cmp_extent is None:
                    QMessageBox.warning(self, "Fold Map",
                        "Extensao da area (nodes/shots) desconhecida -- nao foi possivel binar os resultados.")
                    return
                xmin, xmax, ymin, ymax = self.cmp_extent
            col = int((mx - xmin) / bin_size)
            row = int((my - ymin) / bin_size)
            key = (col, row)
            fold_grid[key] = fold_grid.get(key, 0) + 1

        if self.pairs_error:
            QMessageBox.warning(self, "Fold Map", self.pairs_error)
            return
        if self.pairs_canceled:
            QMessageBox.information(self, "Fold Map", "Calculo cancelado.")
            return
        if not fold_grid:
            QMessageBox.information(self, "Fold Map",
                "Nenhum par fonte-receptor encontrado na faixa de offset [%s, %s] m."
                % (min_offset, max_offset))
            return

        fold_layer = QgsVectorLayer(
            "Polygon?crs=epsg:31983&field=fold:integer", "fold_map", "memory")
        prov = fold_layer.dataProvider()
        feats = []
        for (col, row), count in fold_grid.items():
            x0 = xmin + col * bin_size
            y0 = ymin + row * bin_size
            x1 = x0 + bin_size
            y1 = y0 + bin_size
            ring = [QgsPointXY(x0, y0), QgsPointXY(x1, y0),
                    QgsPointXY(x1, y1), QgsPointXY(x0, y1), QgsPointXY(x0, y0)]
            geom = QgsGeometry.fromPolygonXY([ring])
            feat = QgsFeature()
            feat.setGeometry(geom)
            feat.setAttributes([count])
            feats.append(feat)
        prov.addFeatures(feats)
        fold_layer.updateExtents()

        self.applyFoldRenderer(fold_layer)

        self.replaceLayerInLay('fold_map', fold_layer)
        self.actShowFoldLayer.setChecked(True)
        self.showVisibleMapLayers()

        fold_values = list(fold_grid.values())
        cache_note = ("" if self.pairs_from_cache else
                     "\n\nCache CMP salvo em: %s" % self.cmp_file)
        QMessageBox.information(self, "Fold Map",
            "Fold calculado (offset %s - %s m): %d bins, fold minimo = %d, fold maximo = %d%s"
            % (min_offset, max_offset, len(fold_grid), min(fold_values), max(fold_values), cache_note))

    def computeAzimuthMap(self):
        """ Compute an azimuth map (mean source-receiver azimuth per CMP bin)
        from the 'nodes' (receivers) and 'shots' (sources) layers. """

        bin_size, ok1 = QInputDialog.getDouble(self, "Azimuth Map",
            "Tamanho do bin (m):", 100.0, 1.0, 100000.0, 1)
        if not ok1:
            return

        min_offset, ok2 = QInputDialog.getDouble(self, "Azimuth Map",
            "Offset minimo (m):", 0.0, 0.0, 1000000.0, 1)
        if not ok2:
            return

        max_offset, ok3 = QInputDialog.getDouble(self, "Azimuth Map",
            "Offset maximo (m):", 6000.0, 0.0, 1000000.0, 1)
        if not ok3:
            return

        if min_offset >= max_offset:
            QMessageBox.warning(self, "Azimuth Map",
                "Offset minimo deve ser menor que o offset maximo.")
            return

        xmin = ymin = None
        # (col, row) -> [sum_sin, sum_cos, count]  (circular accumulation)
        azimuth_grid = {}
        for mx, my, offset, azimuth in self.getSourceReceiverPairs(
                min_offset, max_offset, "Calculando mapa de azimute..."):
            if xmin is None:
                if self.cmp_extent is None:
                    QMessageBox.warning(self, "Azimuth Map",
                        "Extensao da area (nodes/shots) desconhecida -- nao foi possivel binar os resultados.")
                    return
                xmin, xmax, ymin, ymax = self.cmp_extent
            col = int((mx - xmin) / bin_size)
            row = int((my - ymin) / bin_size)
            key = (col, row)
            rad = math.radians(azimuth)
            if key not in azimuth_grid:
                azimuth_grid[key] = [0.0, 0.0, 0]
            acc = azimuth_grid[key]
            acc[0] += math.sin(rad)
            acc[1] += math.cos(rad)
            acc[2] += 1

        if self.pairs_error:
            QMessageBox.warning(self, "Azimuth Map", self.pairs_error)
            return
        if self.pairs_canceled:
            QMessageBox.information(self, "Azimuth Map", "Calculo cancelado.")
            return
        if not azimuth_grid:
            QMessageBox.information(self, "Azimuth Map",
                "Nenhum par fonte-receptor encontrado na faixa de offset [%s, %s] m."
                % (min_offset, max_offset))
            return

        azimuth_layer = QgsVectorLayer(
            "Polygon?crs=epsg:31983&field=azimuth:double", "azimuth_map", "memory")
        prov = azimuth_layer.dataProvider()
        feats = []
        mean_azimuths = []
        for (col, row), (sum_sin, sum_cos, count) in azimuth_grid.items():
            mean_az = math.degrees(math.atan2(sum_sin / count, sum_cos / count))
            if mean_az < 0:
                mean_az += 360.0
            mean_azimuths.append(mean_az)

            x0 = xmin + col * bin_size
            y0 = ymin + row * bin_size
            x1 = x0 + bin_size
            y1 = y0 + bin_size
            ring = [QgsPointXY(x0, y0), QgsPointXY(x1, y0),
                    QgsPointXY(x1, y1), QgsPointXY(x0, y1), QgsPointXY(x0, y0)]
            geom = QgsGeometry.fromPolygonXY([ring])
            feat = QgsFeature()
            feat.setGeometry(geom)
            feat.setAttributes([mean_az])
            feats.append(feat)
        prov.addFeatures(feats)
        azimuth_layer.updateExtents()

        self.applyAzimuthRenderer(azimuth_layer)

        self.replaceLayerInLay('azimuth_map', azimuth_layer)
        self.actShowAzimuthLayer.setChecked(True)
        self.showVisibleMapLayers()

        cache_note = ("" if self.pairs_from_cache else
                     "\n\nCache CMP salvo em: %s" % self.cmp_file)
        QMessageBox.information(self, "Azimuth Map",
            "Azimute calculado (offset %s - %s m): %d bins, azimute medio min = %d, max = %d graus%s"
            % (min_offset, max_offset, len(azimuth_grid), round(min(mean_azimuths)), round(max(mean_azimuths)), cache_note))

    def computeFoldRose(self):
        """ Compute the fold (trace count) distribution binned by azimuth
        sector and offset ring, from the 'nodes' (receivers) and 'shots'
        (sources) layers, and show it as an offset-azimuth polar diagram
        (rings = offset, color = fold count). """

        n_sectors, ok0 = QInputDialog.getInt(self, "Fold Rose",
            "Numero de setores de azimute:", 16, 4, 72, 4)
        if not ok0:
            return

        n_rings, ok1 = QInputDialog.getInt(self, "Fold Rose",
            "Numero de faixas (aneis) de offset:", 6, 1, 50, 1)
        if not ok1:
            return

        min_offset, ok2 = QInputDialog.getDouble(self, "Fold Rose",
            "Offset minimo (m):", 0.0, 0.0, 1000000.0, 1)
        if not ok2:
            return

        max_offset, ok3 = QInputDialog.getDouble(self, "Fold Rose",
            "Offset maximo (m):", 6000.0, 0.0, 1000000.0, 1)
        if not ok3:
            return

        if min_offset >= max_offset:
            QMessageBox.warning(self, "Fold Rose",
                "Offset minimo deve ser menor que o offset maximo.")
            return

        sector_width = 360.0 / n_sectors
        ring_width = (max_offset - min_offset) / n_rings

        counts = [[0] * n_sectors for _ in range(n_rings)]   # counts[ring][sector]
        for mx, my, offset, azimuth in self.getSourceReceiverPairs(
                min_offset, max_offset, "Calculando fold rose..."):
            sector = int(azimuth / sector_width) % n_sectors
            ring = int((offset - min_offset) / ring_width)
            if ring >= n_rings:
                ring = n_rings - 1
            counts[ring][sector] += 1

        if self.pairs_error:
            QMessageBox.warning(self, "Fold Rose", self.pairs_error)
            return
        if self.pairs_canceled:
            QMessageBox.information(self, "Fold Rose", "Calculo cancelado.")
            return
        if sum(sum(r) for r in counts) == 0:
            QMessageBox.information(self, "Fold Rose",
                "Nenhum par fonte-receptor encontrado na faixa de offset [%s, %s] m."
                % (min_offset, max_offset))
            return

        self.showFoldRoseDialog(counts, n_sectors, n_rings, min_offset, max_offset)

    def showFoldRoseDialog(self, counts, n_sectors, n_rings, min_offset, max_offset):
        """ Display the fold-by-azimuth/offset counts as a polar heatmap:
        angle = azimuth, radius = offset ring, color = fold count. """

        try:
            import matplotlib
            matplotlib.use('Qt5Agg')
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            import numpy as np
        except ImportError:
            QMessageBox.warning(self, "Fold Rose",
                "A biblioteca matplotlib nao esta disponivel neste ambiente Python do QGIS.\n"
                "Instale com: pip install matplotlib (no mesmo Python usado pelo QGIS).")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Fold Rose - offset %s - %s m" % (min_offset, max_offset))
        dialog.resize(700, 700)
        layout = QVBoxLayout(dialog)

        fig = Figure(figsize=(6.5, 6.5))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        ax = fig.add_subplot(111, projection='polar')
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)

        theta_edges = np.radians(np.linspace(0.0, 360.0, n_sectors + 1))
        r_edges = np.linspace(min_offset, max_offset, n_rings + 1)
        Theta, R = np.meshgrid(theta_edges, r_edges)
        C = np.array(counts)   # shape (n_rings, n_sectors)

        mesh = ax.pcolormesh(Theta, R, C, cmap='jet', shading='flat')
        fig.colorbar(mesh, ax=ax, pad=0.1, label='Fold')

        ax.set_title("Fold por azimute x offset (%d setores, %d aneis)"
                     % (n_sectors, n_rings), va='bottom')

        dialog.setLayout(layout)
        dialog.exec_()

    def applyFoldRenderer(self, layer):
        """ Apply a graduated color renderer (blue -> red) on the 'fold' field. """

        values = [f['fold'] for f in layer.getFeatures()]
        vmin, vmax = min(values), max(values)

        n_classes = 5
        ramp_colors = [QColor(0, 0, 255), QColor(0, 255, 255), QColor(0, 255, 0),
                       QColor(255, 255, 0), QColor(255, 0, 0)]

        step = (vmax - vmin) / float(n_classes) if vmax > vmin else 1.0
        ranges = []
        self.foldRanges = []
        for i in range(n_classes):
            lower = vmin + i * step
            upper = vmax if i == n_classes - 1 else vmin + (i + 1) * step
            symbol = QgsFillSymbol.createSimple({
                'color': ramp_colors[i].name(),
                'outline_color': 'black',
                'outline_width': '0.1'})
            label = "%d - %d" % (round(lower), round(upper))
            ranges.append(QgsRendererRange(lower, upper, symbol, label))
            self.foldRanges.append((lower, upper, ramp_colors[i], label))

        renderer = QgsGraduatedSymbolRenderer('fold', ranges)
        layer.setRenderer(renderer)
        layer.setOpacity(self.foldOpacity)
        layer.triggerRepaint()

        if hasattr(self, 'actShowFoldLegend') and self.actShowFoldLegend.isChecked():
            self.updateFoldLegend()

    def setFoldTransparency(self):
        opacity_pct, ok = QInputDialog.getInt(self, "Transparência do Fold Map",
            "Opacidade (%):", int(self.foldOpacity * 100), 0, 100, 5)
        if not ok:
            return
        self.foldOpacity = opacity_pct / 100.0
        fold_layer = next((x for x in lay if x.name() == 'fold_map'), None)
        if fold_layer:
            fold_layer.setOpacity(self.foldOpacity)
            fold_layer.triggerRepaint()
            self.map_canvas.refresh()
        else:
            QMessageBox.information(self, "Fold Map", "Calcule o Fold Map primeiro.")

    def toggleFoldLegend(self, checked):
        if checked:
            self.updateFoldLegend()
            self.foldLegendDock.show()
        else:
            self.foldLegendDock.hide()

    def updateFoldLegend(self):
        # clear previous legend rows
        while self.foldLegendLayout.count():
            item = self.foldLegendLayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.foldRanges:
            self.foldLegendLayout.addWidget(QLabel("Fold map ainda nao foi calculado."))
            return

        for lower, upper, color, label in self.foldRanges:
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(2, 2, 2, 2)
            swatch = QLabel()
            swatch.setFixedSize(20, 14)
            swatch.setStyleSheet("background-color: %s; border: 1px solid black;" % color.name())
            row_layout.addWidget(swatch)
            row_layout.addWidget(QLabel(label))
            row_widget.setLayout(row_layout)
            self.foldLegendLayout.addWidget(row_widget)
        self.foldLegendLayout.addStretch()

    def applyAzimuthRenderer(self, layer):
        """ Apply a graduated color-wheel renderer on the 'azimuth' field
        (values in degrees, 0-360), using 8 compass sectors. """

        n_classes = 8
        step = 360.0 / n_classes

        ranges = []
        self.azimuthRanges = []
        for i in range(n_classes):
            lower = i * step
            upper = 360.0 if i == n_classes - 1 else (i + 1) * step
            hue = int(round((lower + upper) / 2.0)) % 360
            color = QColor.fromHsv(hue, 200, 230)
            symbol = QgsFillSymbol.createSimple({
                'color': color.name(),
                'outline_color': 'black',
                'outline_width': '0.1'})
            label = "%d - %d graus" % (round(lower), round(upper))
            ranges.append(QgsRendererRange(lower, upper, symbol, label))
            self.azimuthRanges.append((lower, upper, color, label))

        renderer = QgsGraduatedSymbolRenderer('azimuth', ranges)
        layer.setRenderer(renderer)
        layer.setOpacity(self.azimuthOpacity)
        layer.triggerRepaint()

        if hasattr(self, 'actShowAzimuthLegend') and self.actShowAzimuthLegend.isChecked():
            self.updateAzimuthLegend()

    def setAzimuthTransparency(self):
        opacity_pct, ok = QInputDialog.getInt(self, "Transparência do Azimuth Map",
            "Opacidade (%):", int(self.azimuthOpacity * 100), 0, 100, 5)
        if not ok:
            return
        self.azimuthOpacity = opacity_pct / 100.0
        azimuth_layer = next((x for x in lay if x.name() == 'azimuth_map'), None)
        if azimuth_layer:
            azimuth_layer.setOpacity(self.azimuthOpacity)
            azimuth_layer.triggerRepaint()
            self.map_canvas.refresh()
        else:
            QMessageBox.information(self, "Azimuth Map", "Calcule o Azimuth Map primeiro.")

    def toggleAzimuthLegend(self, checked):
        if checked:
            self.updateAzimuthLegend()
            self.azimuthLegendDock.show()
        else:
            self.azimuthLegendDock.hide()

    def updateAzimuthLegend(self):
        # clear previous legend rows
        while self.azimuthLegendLayout.count():
            item = self.azimuthLegendLayout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.azimuthRanges:
            self.azimuthLegendLayout.addWidget(QLabel("Azimuth map ainda nao foi calculado."))
            return

        for lower, upper, color, label in self.azimuthRanges:
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(2, 2, 2, 2)
            swatch = QLabel()
            swatch.setFixedSize(20, 14)
            swatch.setStyleSheet("background-color: %s; border: 1px solid black;" % color.name())
            row_layout.addWidget(swatch)
            row_layout.addWidget(QLabel(label))
            row_widget.setLayout(row_layout)
            self.azimuthLegendLayout.addWidget(row_widget)
        self.azimuthLegendLayout.addStretch()
