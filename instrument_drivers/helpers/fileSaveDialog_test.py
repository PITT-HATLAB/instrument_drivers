from instrument_drivers.helpers.fileSavingDialog import fileNamefromMenu
# from PyQt5.QtWidgets import QFileDialog
# filename = QFileDialog.getSaveFileName("Save file","")
filename = fileNamefromMenu()
#use the app to get a filename, save that with the text "hello" inside
print(f"we got this: {filename}")
file = open(filename, 'w')
file.write("hello")
file.close()