import sys
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon
'''
author: Ryan Kaufman
want to make a file saving dialog so that we can save things from the terminal without having to run a script
in: nothing
out: filepath
'''
# all of this is ripped from here:

class saveApp(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'Choose a location to save your file'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.res = self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        fn = self.saveFileDialog()
        self.show()
        return(fn)

    def saveFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getSaveFileName(self, "QFileDialog.getSaveFileName()", "",
                                                  "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            print(fileName)
            return fileName

def fileNamefromMenu():
    app = QApplication(sys.argv)
    ex = saveApp()
    return ex.res
if __name__ == '__main__':
    res = fileNamefromMenu()

