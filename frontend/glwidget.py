from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer
from obj_loader import ObjLoader
from OpenGL.GL import *
from OpenGL.GLU import *

class GLWidget(QOpenGLWidget):
    FPS = 30

    def __init__(self, obj_path):
        super().__init__()
        self.obj = ObjLoader(obj_path)

        self.timer = QTimer(self)
        self.timer.setInterval(1000 // self.FPS)  # ~33ms per frame
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glLightfv(GL_LIGHT0, GL_POSITION, (5, 5, 5, 1))
        glClearColor(0.05, 0.05, 0.1, 1)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h if h else 1, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, -5)

        for face, material in self.obj.faces:
            if material and material in self.obj.materials:
                glColor3fv(self.obj.materials[material]["Kd"])
            else:
                glColor3f(1, 1, 1)

            glBegin(GL_POLYGON)
            for v_idx, n_idx in face:
                if n_idx is not None:
                    glNormal3fv(self.obj.normals[n_idx])
                glVertex3fv(self.obj.vertices[v_idx])
            glEnd()