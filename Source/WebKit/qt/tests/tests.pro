
TEMPLATE = subdirs
SUBDIRS = qwebframe qwebpage qwebelement qgraphicswebview qwebhistoryinterface qwebview qwebhistory qwebinspector hybridPixmap
contains(QT_CONFIG, declarative): SUBDIRS += qdeclarativewebview
SUBDIRS += benchmarks/painting benchmarks/loading
