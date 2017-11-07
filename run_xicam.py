from qtpy.QtWidgets import *


def main():
    app = QApplication([])

    from xicam.gui.windows import splash

    splash = splash.XicamSplashScreen()
    app.exec_()


if __name__ == '__main__':
    main()
