import sys

from qtpy.QtCore import QTimer, Qt
from qtpy.QtWidgets import QWidget, QLabel, QSizePolicy
from qtpy.QtMultimedia import QMediaPlayer, QMediaPlaylist, QMediaContent
from qtpy.QtMultimediaWidgets import QVideoWidget
from qtpy.QtCore import QUrl
from qtpy.QtWidgets import QApplication, QVBoxLayout, QMainWindow

from xicam.gui import static


def elide(s: str, max_len: int = 60):
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


class XicamSplashScreen(QMainWindow):
    minsplashtime = 5000

    def __init__(self, log_path: str, initial_length: int):
        """
        A QSplashScreen customized to display an animated gif. The splash triggers launch when clicked.

        After minsplashtime, this splash waits until the animation finishes before triggering the launch.

        Parameters
        ----------
        log_path    :   str
            Path to the Xi-CAM log file to reflect
        initial_length: int
            Length in bytes to seek forward before reading
        """

        super(XicamSplashScreen, self).__init__(flags=Qt.WindowStaysOnTopHint | Qt.SplashScreen)

        self.videoWidget = QVideoWidget()
        self.videoWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        playlist = QMediaPlaylist(self.mediaPlayer)
        playlist.setPlaybackMode(QMediaPlaylist.Loop)
        playlist.addMedia(QMediaContent(QUrl.fromLocalFile(str(static.path("images/animated-logo.mp4")))))
        playlist.setCurrentIndex(1)
        self.mediaPlayer.setPlaylist(playlist)
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.play()
        self.mediaPlayer.mediaChanged.connect(self.execlaunch)


        w = QWidget()
        self.setCentralWidget(w)
        self._layout = QVBoxLayout()
        w.setLayout(self._layout)
        w.layout().addWidget(self.videoWidget)
        self.messageWidget = QLabel()
        self.setStyleSheet('background-color:black; color:grey;')
        w.layout().addWidget(self.messageWidget)
        w.layout().setContentsMargins(10,30,10,10)
        # w.layout().setSpacing(0)
        self.setFixedSize(550, 400)

        self.setWindowFlags(Qt.FramelessWindowHint)

        # Setup drawing
        self.messageWidget.setText("Starting Xi-CAM...")

        self._launching = False
        self._launchready = False

        self.log_file = open(log_path, "r")
        self.log_file.seek(initial_length)

        # Start splashing
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.instance().setActiveWindow(self)

        # Setup timed triggers for launching the QMainWindow
        self.finish_timer = QTimer(self)
        self.finish_timer.singleShot(self.minsplashtime, self.execlaunch)

        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self.showMessageFromLog)
        self.message_timer.start(1./60)

    def showMessageFromLog(self):
        line = self.log_file.readline().strip()
        if line:
            self.showMessage(elide(line.split(">")[-1]))

    def showMessage(self, message: str):
        # attempt to parse out everyting besides the message
        try:
            message=message.split(" - ")[-1]
        except Exception:
            pass
        else:
            self.messageWidget.setText(elide(message))

    def mousePressEvent(self, *args, **kwargs):
        self.finish_timer.stop()
        self.execlaunch()

    def show(self):
        """
        Start the animation when shown
        """
        super(XicamSplashScreen, self).show()

    def execlaunch(self):
        """
        Launch the mainwindow
        """
        if not self._launching:
            self._launching = True

            self.finish_timer.stop()

            # Stop splashing
            self.hide()
            self.close()
            QApplication.instance().quit()


def main():
    qapp = QApplication([])
    splash = XicamSplashScreen(sys.argv[-2], int(sys.argv[-1]))
    # splash = XicamSplashScreen('C:\\Users\LBL\\AppData\\Local\\CAMERA\\xicam\\Cache\\logs\\out.log', 1)
    splash.show()
    qapp.exec_()


if __name__ == "__main__":
    main()
