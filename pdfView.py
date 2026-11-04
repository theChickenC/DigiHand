import constants
import utils
from PySide6.QtGui import QFont, QImage, QTextDocument
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QMessageBox
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument


class PdfView(QPdfView):
    def __init__(self, pdf_doc):
        super().__init__()
        # self.setAutoFormatting(QPdfView.AutoFormattingFlag.AutoAll)
        # Initialize default font size.
        font = QFont("Times", 12)
        self.setFont(font)
        self.pdf_doc = pdf_doc
    
    def zoomIn(self):
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        zoom = self.zoomFactor() 
        self.setZoomFactor(zoom + 0.2)
        # QMessageBox.information(self, "Info", "zoomIn() gets called.")
        return

    def zoomOut(self):
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        zoom = self.zoomFactor() 
        self.setZoomFactor(zoom - 0.2)
        # QMessageBox.information(self, "Info", "zoomOut() gets called.")
        return
    
    def zoomFit(self):
        self.setZoomMode(QPdfView.ZoomMode.FitInView)
        # QMessageBox.information(self, "Info", "zoomFit() gets called.")
        return
    
    def zoomOG(self):
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        self.setZoomFactor(1)
        # QMessageBox.information(self, "Info", "zoomOG() gets called.")
        return
    
    def rotateL(self):
        angle = self.pageRotation()
        self.setPageRotation( (angle - 90) % 360)
        # QMessageBox.information(self, "Info", "rotateL() gets called.")
        
        return
    
    def rotateR(self):
        angle = self.pageRotation()
        self.setPageRotation( (angle + 90) % 360)
        # QMessageBox.information(self, "Info", "rotateR() gets called.")
        return
    
    def firstPage(self):
        # QMessageBox.information(self, "Info", "firstPage() gets called.")
        nav = self.pageNavigator()
        cur = nav.currentPage()
        nav.jump(0, QPointF(0, 0))
        return
    
    def prevPage(self):
        nav = self.pageNavigator()
        cur = nav.currentPage()
        if cur > 0:
            # jump(page, position, zoom=0 keeps current zoom)
            nav.jump(cur - 1, QPointF(0, 0))    

    def nextPage(self):
        # QMessageBox.information(self, "Info", "nextPage() gets called.")
        nav = self.pageNavigator()
        cur = nav.currentPage()
        numPages = self.pdf_doc.pageCount()
        if cur < numPages - 1:
            # jump(page, position, zoom=0 keeps current zoom)
            nav.jump(cur + 1, QPointF(0, 0))        
        return

    def lastPage(self):
        # QMessageBox.information(self, "Info", "lastPage() gets called.")
        nav = self.pageNavigator()
        cur = nav.currentPage()
        numPages = self.pdf_doc.pageCount()
        nav.jump(numPages-1, QPointF(0, 0))
        return


    
