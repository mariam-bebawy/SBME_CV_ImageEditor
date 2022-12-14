#### IMPORTS
############################

import os
import sys

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pyqtgraph as pg
import scipy.fftpack as fp
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QFileDialog, QGraphicsScene


############################
#### CONNECT MAIN WINDOW
############################
class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.set_facecolor('#e1e1e1')
        super(MplCanvas, self).__init__(self.fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        ############################
        #### LOAD UI FILE
        ############################

        uic.loadUi(r'Final.ui', self)

        ############################
        #### BUTTON CONNECTIONS
        ############################
        self.cvimg = [[]]
        self.final = [[]]
        self.actionopen.triggered.connect(lambda: self.open())
        self.saveButton.clicked.connect(lambda: self.save())
        self.openButton.clicked.connect(lambda: self.open())
        self.Equalize.clicked.connect(lambda: self.equalizeRGB(self.cvimg))
        self.comboBox.currentIndexChanged.connect(
            lambda: self.spatialFiltering())
        self.filterSize.valueChanged.connect(lambda: self.changeFilterSize())

        ############################
        #### GLOBAL VARIABLES
        ############################
        self.imageview = self.findChild(QLabel, "imageview")
        self.disply_width = 550
        self.display_height = 500
        self.size = self.filterSize.value()
        # self.sliderValue.setText(str(self.filterSize.value()))

        self.histoCanvas = MplCanvas(self, width=5.5, height=4.5, dpi=90)
        self.histoLayout = QtWidgets.QVBoxLayout()
        self.histoCanvas.axes.set_facecolor('#e1e1e1')
        self.histoLayout.addWidget(self.histoCanvas)

        self.fftCanvas = MplCanvas(self, width=5.5, height=4.5, dpi=90)
        self.fftLayout = QtWidgets.QVBoxLayout()
        # self.fftCanvas.axes.set_facecolor('#e1e1e1')
        self.fftLayout.addWidget(self.fftCanvas)

        self.graph = pg.PlotItem()
        self.fftWidget.setCentralItem(self.graph)
        self.histoWidget.setCentralItem(self.graph)
        self.fftWidget.setBackground(QtGui.QColor('#e1e1e1'))
        self.histoWidget.setBackground(QtGui.QColor('#e1e1e1'))
        #31c9ca #7dbeff #00aa7f
        pg.PlotItem.hideAxis(self.graph, 'left')
        pg.PlotItem.hideAxis(self.graph, 'bottom')

    ############################
    #### FUNCTION DEFINITIONS
    ############################
    def open(self):
        self.imagePath = QFileDialog.getOpenFileName(
            self, "Open File", "This PC",
            "All Files (*);;PNG Files(*.png);; Jpg Files(*.jpg)")
        self.cvimg = cv2.imread(self.imagePath[0])
        self.Imgorigin = self.cvimg.copy()
        self.comboBox.setCurrentText("Normal")
        self.OGgray = cv2.cvtColor(self.Imgorigin, cv2.COLOR_BGR2GRAY)
        _, _, self.fft = self.toFFT(self.OGgray)
        #cv image to Qpixmap
        qt_img = self.convertCvQt(self.cvimg)
        # display it
        self.showHistogram(self.OGgray)
        self.displayFFT()
        self.displayImage(qt_img)

    def save(self):
        cv2.imwrite('saved.jpg', self.cvimg)

    def convertCvQt(self, img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h,
                                            bytes_per_line,
                                            QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.disply_width, self.display_height,
                                        Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def changeFilterSize(self):
        self.size = self.filterSize.value()
        self.sliderValue.setText(str(self.size))
        self.spatialFiltering()

    def displayImage(self, qtimg):
        self.imageview.clear()
        self.imageview.setPixmap(qtimg)
        self.sliderValue.setText(str(self.size))

    def displayFFT(self):
        self.fftCanvas.axes.imshow(self.fft, 'gray', aspect="auto")
        self.fftCanvas.axes.axis('off')
        self.fftCanvas.draw()
        self.fftWidget.setCentralItem(self.graph)
        self.fftWidget.setLayout(self.fftLayout)

    def spatialFiltering(self):
        imgFiltered = cv2.cvtColor(self.final, cv2.COLOR_BGR2HSV)
        imgValues = imgFiltered[:, :, 2]
        filter = self.comboBox.currentText()

        if filter == 'Normal':
            _, _, self.fft = self.toFFT(self.OGgray)
            self.final = self.Imgorigin
            imgFiltered = cv2.cvtColor(self.Imgorigin, cv2.COLOR_BGR2HSV)
            imgValues = imgFiltered[:, :, 2]

        if filter == 'Low pass filter':
            F1, F2, fftOG = self.toFFT(imgValues)
            imgValues, self.fft, F2 = self.lowPassFiltering(imgValues, F2)

        elif filter == 'Median filter':
            # median acts as a=low-pass filter ---- blurring effect
            # src : source file ---- ksize: int kernel size
            imgValues = cv2.medianBlur(imgValues, self.size)
            _, _, self.fft = self.toFFT(imgValues)

        elif filter == 'High pass filter':
            F1, F2, fftOG = self.toFFT(imgValues)
            #self.final = cv2.cvtColor(self.Imgorigin, cv2.COLOR_BGR2RGB)
            imgValues, self.fft, F2 = self.highPassFiltering(imgValues, F2)
            # print(F2[0:100,0:100])

        elif filter == 'Laplacian filter':
            # laplacian acts as hig-pass filter ---- edge detector
            # src : source file ---- ddepth : depth of output image ---- ksize : blurring kernel size
            imgValues = cv2.GaussianBlur(imgValues, (3, 3), 0)
            imgValues = cv2.Laplacian(imgValues, cv2.CV_64F,
                                      (self.size, self.size))
            imgValues = np.abs(imgValues)
            _, _, self.fft = self.toFFT(imgValues)
        elif filter == 'Low pass filter spatial':
            imgValues, self.fft = self.lowPassFilterSpatial(imgValues)

        elif filter == 'High pass filter spatial':
            imgValues, self.fft = self.highPassFilterSpatial(imgValues)

        imgFiltered[:, :, 2] = imgValues
        imgFiltered = cv2.cvtColor(imgFiltered, cv2.COLOR_HSV2BGR)
        self.cvimg = imgFiltered
        gray = cv2.cvtColor(self.cvimg, cv2.COLOR_BGR2GRAY)
        imgqt = self.convertCvQt(self.cvimg)
        self.displayImage(imgqt)
        self.displayFFT()
        self.showHistogram(gray)

    def toFFT(self, img):
        F1 = fp.fft2((img).astype(float))
        F2 = fp.fftshift(F1)
        plt.figure()
        plt.plot(F2)
        fft = (20 * np.log10(0.1 + F2)).astype(int)
        return F1, F2, fft

    def lowPassFilterSpatial(self, img):
        m, n = img.shape
        # Develop Averaging filter(3, 3) mask
        mask = np.ones([3, 3], dtype=int)
        mask = mask / 9
        # Convolve the 3X3 mask over the image
        img_new = np.zeros([m, n])

        for i in range(1, m - 1):
            for j in range(1, n - 1):
                temp = img[i - 1, j - 1] * mask[0, 0] + img[i - 1, j] * mask[
                    0, 1] + img[i - 1, j + 1] * mask[0, 2] + img[
                        i, j - 1] * mask[1, 0] + img[i, j] * mask[1, 1] + img[
                            i, j + 1] * mask[1, 2] + img[i + 1, j - 1] * mask[
                                2, 0] + img[i + 1, j] * mask[2, 1] + img[
                                    i + 1, j + 1] * mask[2, 2]
                img_new[i, j] = temp
        _, _, fft = self.toFFT(img_new)
        return img_new, fft

    def high_pass_freq_filter(self, img):
        try:
            flag = 0
            _, _ = img.shape
            dft = np.fft.fft2(img)
        except:
            flag = 1
            img = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            dft = np.fft.fft2(img[:, :, 2])

        dft_shift = np.fft.fftshift(dft)
        magnitude_spectrum = 20 * np.log(np.abs(dft_shift) + 1)

        rows, cols = dft.shape
        crow, ccol = int(rows / 2), int(cols / 2)
        mask = np.ones((rows, cols), np.uint8)

        r = 40
        center = [crow, ccol]
        x, y = np.ogrid[:rows, :cols]
        mask_area = (x - center[0]) * 2 + (y - center[1]) * 2 <= r * r
        mask[mask_area] = 0
        # apply mask and inverse DFT
        fshift = dft_shift * mask
        #--------------------------------------------------------------------------------------------------
        # revers from the freq domain to spatial domain

        fshift_mask_mag = 20 * np.log(np.abs(fshift) + 1)

        f_ishift = np.fft.ifftshift(fshift)
        img_back = np.fft.ifft2(f_ishift)
        img_filtered = np.abs(img_back)

        if (flag == 1):
            img[:, :, 2] = img_filtered
            img = cv2.cvtColor(img, cv2.COLOR_HSV2RGB)
            return img, magnitude_spectrum, fshift_mask_mag

        return img_filtered, magnitude_spectrum, fshift_mask_mag

    def highPassFilterSpatial(self, img):
        m, n = img.shape
        # Develop Averaging filter(3, 3) mask
        mask = np.ones([3, 3], dtype=int)
        mask = mask / -9
        mask[2, 2] = mask[2, 2] * -8
        # mask = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]])
        # Convolve the 3X3 mask over the image
        img_new = np.zeros([m, n])

        for i in range(1, m - 1):
            for j in range(1, n - 1):
                temp = img[i - 1, j - 1] * mask[0, 0] + img[i - 1, j] * mask[
                    0, 1] + img[i - 1, j + 1] * mask[0, 2] + img[
                        i, j - 1] * mask[1, 0] + img[i, j] * mask[1, 1] + img[
                            i, j + 1] * mask[1, 2] + img[i + 1, j - 1] * mask[
                                2, 0] + img[i + 1, j] * mask[2, 1] + img[
                                    i + 1, j + 1] * mask[2, 2]
                img_new[i, j] = temp

        img_new = np.abs(img_new)
        _, _, fft = self.toFFT(img_new)
        return img_new, fft

    def highPassFiltering(self, img, F2):
        (w, h) = img.shape
        half_w, half_h = int(w / 2), int(h / 2)
        F2[half_w - self.size:half_w + self.size + 1,
           half_h - self.size:half_h + self.size +
           1] = 0  # select all but the first 50x50 (low) frequencies
        fft = (20 * np.log10(0.1 + F2)).astype(int)
        img = np.abs(fp.ifft2(fp.ifftshift(F2)))
        return img, fft, F2

    def lowPassFiltering(self, img, F2):
        (w, h) = img.shape
        half_w, half_h = int(w / 2), int(h / 2)
        Fblank = np.zeros((w, h), np.uint8)
        # select the first 30x30 frequencies
        Fblank[half_w - self.size:half_w + self.size + 1,
               half_h - self.size:half_h + self.size + 1] = 1
        F2 = Fblank * F2
        fft = (20 * np.log10(0.1 + F2)).astype(int)
        img = np.abs(fp.ifft2(fp.ifftshift(F2)))
        return img, fft, F2

    def createHistoArray(self, img):
        Histo = np.zeros(shape=(256, 1))
        shape = img.shape
        for horizontal in range(shape[0]):
            for vertical in range(shape[1]):
                temp = img[horizontal, vertical]
                Histo[temp, 0] = Histo[temp, 0] + 1
        return Histo

    #Reditributes the grayscale to be applied on images later on
    #Ex: if we have an Input = [0,1,2,3,4,5,6,7] , Output = [0,1,2,3,3,3,4,5]

    def redistributeGrayScale(self, histoArray, img):
        cumu = np.array([])
        cumu = np.append(cumu, img[0, 0])
        shape = img.shape
        for i in range(255):
            temp = histoArray[0, i + 1] + cumu[i]
            cumu = np.append(cumu, temp)
        max = np.amax(img)
        cumu = np.round((cumu / (shape[0] * shape[1])) * max)
        return cumu

    #Maps new values for the pixels of the image according to the new distribution of GrayScale generated earlier

    def mapPixels(self, cumu, original):
        img = np.full_like(original, 0)
        shape = original.shape
        for i in range(shape[0]):
            for j in range(shape[1]):
                temp = original[i, j]
                img[i, j] = cumu[temp]
        return img

    #Call this function to equalize your histogram

    def showHistogram(self, data):
        self.histoCanvas.axes.clear()
        no_of_bins = np.arange(256)
        data_rav = data.ravel()  #spreads image pixels into one dimension
        self.histoCanvas.axes.hist(data_rav, bins=no_of_bins)
        self.histoCanvas.draw()
        self.histoWidget.setCentralItem(self.graph)
        self.histoWidget.setLayout(self.histoLayout)

    def equalize(self, img):
        #img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        histoArray = self.createHistoArray(img)
        histoArray = np.transpose(histoArray)
        redistributedGrayScale = self.redistributeGrayScale(histoArray, img)
        equalized_img = self.mapPixels(redistributedGrayScale, img)
        return equalized_img

    def createRGB(self, r, g, b):
        rgb = np.dstack((r, g, b))
        return rgb

    def equalizeRGB(self, img):
        r = img[:, :, 2]
        g = img[:, :, 1]
        b = img[:, :, 0]

        r_eq = self.equalize(r)
        g_eq = self.equalize(g)
        b_eq = self.equalize(b)

        self.final = self.createRGB(b_eq, g_eq, r_eq)
        self.showHistogram(self.final)
        img = self.convertCvQt(self.final)
        self.OGgray = cv2.cvtColor(self.final, cv2.COLOR_RGB2GRAY)
        _, _, self.fft = self.toFFT(self.OGgray)
        self.displayImage(img)
        self.displayFFT()


############################
#### CALL MAIN FUNCTION
############################


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
