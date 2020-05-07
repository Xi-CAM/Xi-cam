import sys
from qtpy.QtCore import QTimer, Qt
from qtpy.QtGui import QMovie, QPixmap
from qtpy.QtWidgets import QSplashScreen, QApplication

from xicam.gui import static


def elide(s: str, max_len: int = 60):
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


class XicamSplashScreen(QSplashScreen):
    minsplashtime = 5000

    def __init__(self, log_path: str, initial_length: int, f: int = Qt.WindowStaysOnTopHint | Qt.SplashScreen):
        """
        A QSplashScreen customized to display an animated gif. The splash triggers launch when clicked.

        After minsplashtime, this splash waits until the animation finishes before triggering the launch.

        Parameters
        ----------
        log_path    :   str
            Path to the Xi-CAM log file to reflect
        initial_length: int
            Length in bytes to seek forward before reading
        f           :   int
            Extra flags (see base class)
        """

        # Get logo movie from relative path
        self.movie = QMovie(str(static.path("images/animated_logo.gif")))

        # Setup drawing
        self.movie.frameChanged.connect(self.paintFrame)
        self.movie.jumpToFrame(1)
        self.pixmap = QPixmap(self.movie.frameRect().size())
        super(XicamSplashScreen, self).__init__(self.pixmap, f)
        self.setMask(self.pixmap.mask())
        self.movie.finished.connect(self.restartmovie)
        self.showMessage("Starting Xi-CAM...")

        self._launching = False
        self._launchready = False
        self.timer = QTimer(self)

        self.log_file = open(log_path, "r")
        self.log_file.seek(initial_length)

        # Start splashing
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.instance().setActiveWindow(self)

        # Setup timed triggers for launching the QMainWindow
        self.timer.singleShot(self.minsplashtime, self.launchwindow)

    def showMessage(self, message: str, color=Qt.darkGray):
        # attempt to parse out everyting besides the message
        try:
            message=message.split(" - ")[-1]
        except Exception:
            pass
        else:
            super(XicamSplashScreen, self).showMessage(elide(message), color=color, alignment=Qt.AlignBottom)

    def mousePressEvent(self, *args, **kwargs):
        # TODO: Apparently this doesn't work?
        self.timer.stop()
        self.execlaunch()

    def show(self):
        """
        Start the animation when shown
        """
        super(XicamSplashScreen, self).show()
        self.movie.start()

    def paintFrame(self):
        """
        Paint the current frame
        """
        self.pixmap = self.movie.currentPixmap()
        self.setMask(self.pixmap.mask())
        self.setPixmap(self.pixmap)
        self.movie.setSpeed(self.movie.speed() + 20)

        line = self.log_file.readline().strip()
        if line:
            self.showMessage(elide(line.split(">")[-1]))

    def sizeHint(self):
        return self.movie.scaledSize()

    def restartmovie(self):
        """
        Once the animation reaches the end, check if its time to launch, otherwise restart animation
        """
        if self._launchready:
            self.execlaunch()
            return
        self.movie.start()

    def launchwindow(self):
        """
        Save state, defer launch until animation finishes
        """
        self._launchready = True

    def execlaunch(self):
        """
        Launch the mainwindow
        """
        if not self._launching:
            self._launching = True

            self.timer.stop()

            # Stop splashing
            self.hide()
            self.movie.stop()
            self.close()
            QApplication.instance().quit()


if __name__ == "__main__":
    qapp = QApplication([])
    splash = XicamSplashScreen(sys.argv[-2], int(sys.argv[-1]))
    qapp.exec_()
