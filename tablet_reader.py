#Standardlib
import socket
import pickle
#Extern Packages
from PyQt5.QtGui import QTabletEvent
from PyQt5.QtWidgets import QWidget, QApplication
import numpy as np

class TabletSampleWindow(QWidget):
    def __init__(self, app, sock, parent=None):
        super(TabletSampleWindow, self).__init__(parent)
        # Resizing the sample window to full desktop size:
        frame_rect = app.desktop().frameGeometry()
        width, height = frame_rect.width(), frame_rect.height()
        self.resize(width, height)
        self.move(-9, 0)
        self.setWindowTitle("Sample Tablet Event Handling")
        self.sock = sock

    def tabletEvent(self, tabletEvent : QTabletEvent):
        self.sock.sendto(pickle.dumps(np.array([[int(tabletEvent.pressure()*1000)]])),('127.0.0.1', 3001))
        tabletEvent.accept()
        
def main_tab():        
    app = QApplication([])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto('tablet1'.encode('utf-8'),('127.0.0.1', 3001))
    #sock.recv(64)
    mainform = TabletSampleWindow(app, sock)
    mainform.show()
    app.exec_()

#main_tab()