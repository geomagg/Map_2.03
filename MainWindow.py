class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.setWindowTitle("OBN Design")
        self.setGeometry(500, 500, 1400, 800)

        self.project = QgsProject()

        global lay
        lay=[]
        global curr_dir
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        self.initUI()


#---------------------------Searching for nodes.txt, shots.txt and sail.txt --------------------------------

        curr_d = os.path.abspath(os.path.realpath(os.curdir))
        print ('curr_d', curr_d)
        nodespath = "/nodes.txt"
        filename = "file://"+curr_d+nodespath  
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "nodes", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)
#             print(layer.name())
#             QMessageBox.about(self, "LAYER LOADED!", "Nodes txt layer  loaded")
#        else:
#             QMessageBox.about(self, "LAYER NOT LOADED", "Nodes txt-delimited NOT loaded")


        shotspath = "/shots.txt"
        filename = "file://"+curr_d+shotspath   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "shots", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)
#             QMessageBox.about(self, "LAYER LOADED!", "Shots txt layer  loaded")
#        else:
#             QMessageBox.about(self, "LAYER NOT LOADED", "Shots txt-delimited NOT loaded")


        sailpath = "/sail.txt"
        filename = "file://"+curr_d+sailpath   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "sail", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)
#             QMessageBox.about(self, "LAYER LOADED!", "Sail txt layer  loaded")
#        else:
#             QMessageBox.about(self, "LAYER NOT LOADED", "Sail txt-delimited NOT loaded")



        gridpath = "/grid.txt"
        filename = "file://"+curr_d+gridpath   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "grid", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)
#             QMessageBox.about(self, "LAYER LOADED!", "Grid txt layer  loaded")
#        else:
#             QMessageBox.about(self, "LAYER NOT LOADED", "Grid txt-delimited NOT loaded")








#------------------------------Searching for plo2.txt and polshot.txt-----------

        pol2path = "/pol2.txt"
        filename = "file://"+curr_d+pol2path   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "pol2", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)
#             QMessageBox.about(self, "LAYER LOADED!", "Pol2 txt layer  loaded")
#        else:
#             QMessageBox.about(self, "LAYER NOT LOADED", "Pol2 txt-delimited NOT loaded")

        pol3path = "/polshot.txt"
        filename = "file://"+curr_d+pol3path   
        uri=filename+"?delimiter=%s&crs=epsg:31983&LField=%s&SField=%s&xField=%s&yField=%s" % ("  ", "L", "S", "X", "Y")
        layer = QgsVectorLayer(uri, "polshot", "delimitedtext")
#        if layer.isValid():
        lay.append(layer)
#             QMessageBox.about(self, "LAYER LOADED!", "Pol3 txt layer  loaded")
#        else:
#             QMessageBox.about(self, "LAYER NOT LOADED", "Pol3 txt-delimited NOT loaded")
