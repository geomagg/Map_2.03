def Map(app):
    from mapMenu import MainWindow
    # set up QGIS
    app.setPrefixPath("/usr", True)
    app.initQgis()

    # set the main window and show it
    mw = MainWindow()
    mw.show()
    app.exec_()
