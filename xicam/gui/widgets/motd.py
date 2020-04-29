from qtpy.QtWidgets import QScrollArea, QLabel

from xicam.gui.static import path


class MOTD(QScrollArea):
    def __init__(self, parent=None):
        super(MOTD, self).__init__()
        text = f"""
        <div align='center'>
           <br />
           <br />
           <img src='{path('images/camera.jpg')}' width='200'/>
           <h1 style='font-family:Zero Threes;'>
               Welcome to Xi-cam
           </h1>
           <br />
           Please cite Xi-cam in published work: <br />
           <a href="http://scripts.iucr.org/cgi-bin/paper?S1600577518005787" style="color:white;">Pandolfi, R. J., et al. (2018). J. Synchrotron Rad. <b>25</b>, 1261-1270.</a>
    
        </div>
        
        <table cellspacing="10"><tr><td>
            Ronald J. Pandolfi<sup>a</sup><br />
            Daniel B. Allan<sup>e</sup> <br />
            Elke Arenholz<sup>a</sup> <br />
            Luis Barroso-Luque<sup>a</sup><br />
            Stuart I. Campbell<sup>e</sup><br />
            Thomas A. Caswell<sup>e</sup><br />
            Austin Blair<sup>a</sup><br />
            Francesco De Carlo<sup>c</sup><br />
            Sean Fackler<sup>a</sup><br />
            Amanda P. Fournier<sup>b</sup><br />
            Guillaume Freychet<sup>a</sup><br />
            Masafumi Fukuto<sup>e</sup><br />
            Dŏga G̈ursoy<sup>ch</sup><br />
            Zhang Jiang<sup>c</sup><br />
            Harinarayan Krishnan<sup>a</sup><br />
            Dinesh Kumar<sup>a</sup><br />
            R. Joseph Kline<sup>g</sup><br />
            Ruipeng Li<sup>e</sup><br />
            Christopher Liman<sup>g</sup><br />
        </td><td>
            Stefano Marchesini<sup>a</sup><br />
            Apurva Mehta<sup>b</sup><br />
            Alpha T. N’Diaye<sup>a</sup><br />
            Dilworth (Dula) Y. Parkinson<sup>a</sup><br />
            Holden Parks<sup>a</sup><br />
            Lenson A. Pellouchoud<sup>a</sup><br />
            Talita Perciano<sup>a</sup><br />
            Fang Ren<sup>b</sup><br />
            Shreya Sahoo<sup>a</sup><br />
            Joseph Strzalka<sup>c</sup><br />
            Daniel Sunday<sup>g</sup><br />
            Christopher J. Tassone<sup>a</sup><br />
            Daniela Ushizima<sup>a</sup><br />
            Singanallur Venkatakrishnan<sup>d</sup><br />
            Kevin G. Yager<sup>f</sup><br />
            James A. Sethian<sup>a</sup><br />
            Alexander Hexemer<sup>a</sup>
        </td><td>
            <sup>a</sup>Lawrence Berkeley National Laboratory<br />
            <sup>b</sup>Stanford Synchrotron Radiation Lightsource<br />
            <sup>c</sup>Advanced Photon Source, Argonne National Laboratory<br />
            <sup>d</sup>Oak Ridge National Laboratory<br />
            <sup>e</sup>National Synchrotron Light Source II<br />
            <sup>f</sup>Center for Functional Nanomaterials<br />
            <sup>g</sup>National Institute of Standards and Technology<br />
            <sup>h</sup>Department of Electrical Engineering<br />and Computer Science, Northwestern University<br />
        </td></tr></table>
        
        """

        label = QLabel()
        label.setText(text)
        self.setWidget(label)
