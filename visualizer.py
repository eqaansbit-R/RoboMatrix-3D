"""RoboMatrix 3D interactive rigid-body kinematics visualizer."""

import hashlib
import sys

import numpy as np
from PyQt5.QtCore import QRect, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtOpenGL import QGLFormat, QGLWidget
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplashScreen,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_BLEND,
    GL_LINES,
    GL_LINE_SMOOTH,
    GL_LINE_SMOOTH_HINT,
    GL_MODELVIEW,
    GL_MULTISAMPLE,
    GL_NICEST,
    GL_PROJECTION,
    GL_SRC_ALPHA,
    GL_ONE_MINUS_SRC_ALPHA,
    glBegin,
    glBlendFunc,
    glClear,
    glClearColor,
    glColor3f,
    glColor4f,
    glEnable,
    glEnd,
    glHint,
    glLineWidth,
    glLoadIdentity,
    glMatrixMode,
    glVertex3f,
    glViewport,
)
from OpenGL.GLU import gluLookAt, gluPerspective


class RoboMatrixSplashScreen(QSplashScreen):
    """Minimal centered splash card shown while the application opens."""

    def __init__(self):
        pixmap = QPixmap(800, 450)
        pixmap.fill(QColor("#0F1012"))
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)

    def drawContents(self, painter):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(QColor("#00FFCC"))
        painter.setFont(QFont("Impact", 44, QFont.Bold))
        painter.drawText(
            QRect(0, 125, 800, 70),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "RoboMatrix 3D",
        )
        painter.setPen(QColor("#5C6066"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Normal))
        painter.drawText(
            QRect(0, 230, 800, 40),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "Developed by Zainab & Co. Robotics",
        )


class EngineeringLogo(QWidget):
    """Paint a compact RGB coordinate-frame mark with antialiased lines."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 58)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        origin_x, origin_y = 29, 30
        axes = (
            (QColor("#ff4545"), (origin_x, origin_y), (52, 41)),
            (QColor("#45e879"), (origin_x, origin_y), (7, 42)),
            (QColor("#438cff"), (origin_x, origin_y), (29, 5)),
        )
        for color, start, end in axes:
            pen = QPen(color, 3.0, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(*start, *end)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#eafefa"))
        painter.drawEllipse(origin_x - 2, origin_y - 2, 4, 4)
        painter.end()
        event.accept()


class OpenGLViewport(QGLWidget):
    """Compatibility-profile OpenGL viewport for the scene and coordinate frame."""

    def __init__(self, parent=None):
        gl_format = QGLFormat()
        gl_format.setSampleBuffers(True)
        gl_format.setSamples(4)
        super().__init__(gl_format, parent)
        self.setMinimumSize(320, 240)
        self.rotation_matrix = np.identity(3, dtype=float)
        self.position = np.zeros(3, dtype=float)
        self.camera_azimuth = 45.0
        self.camera_elevation = 32.0
        self.camera_distance = 10.0
        self._last_mouse_position = None
        self.setMouseTracking(True)

    def initializeGL(self):
        glClearColor(20 / 255.0, 20 / 255.0, 20 / 255.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        if self.format().sampleBuffers() and self.format().samples() > 0:
            glEnable(GL_MULTISAMPLE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, width, height):
        height = max(height, 1)
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, width / height, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        azimuth = np.radians(self.camera_azimuth)
        elevation = np.radians(self.camera_elevation)
        eye_x = self.camera_distance * np.cos(elevation) * np.sin(azimuth)
        eye_y = self.camera_distance * np.sin(elevation)
        eye_z = self.camera_distance * np.cos(elevation) * np.cos(azimuth)
        gluLookAt(
            eye_x, eye_y, eye_z,
            0.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
        )

        self._draw_grid()
        self._draw_coordinate_frame()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_mouse_position = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._last_mouse_position is not None:
            current_position = event.pos()
            delta = current_position - self._last_mouse_position
            self._last_mouse_position = current_position
            self.camera_azimuth = (
                self.camera_azimuth + delta.x() * 0.45
            ) % 360.0
            self.camera_elevation = float(
                np.clip(self.camera_elevation - delta.y() * 0.35, -88.0, 88.0)
            )
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_mouse_position = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        angle_delta = event.angleDelta().y()
        pixel_delta = event.pixelDelta().y()
        wheel_delta = angle_delta / 120.0 if angle_delta else pixel_delta / 120.0
        if wheel_delta:
            self.camera_distance = float(
                np.clip(
                    self.camera_distance * np.exp(-wheel_delta * 0.12),
                    2.0,
                    20.0,
                )
            )
            self.update()
            event.accept()
            return
        super().wheelEvent(event)

    def set_transform(self, rotation_matrix, position):
        self.rotation_matrix = np.array(rotation_matrix, dtype=float, copy=True)
        self.position = np.array(position, dtype=float, copy=True)
        self.update()

    def reset_camera(self):
        """Restore the initial orbit view alongside resetting the pose sliders."""
        self.camera_azimuth = 45.0
        self.camera_elevation = 32.0
        self.camera_distance = 10.0
        self.update()

    @staticmethod
    def _draw_grid():
        """Draw a low-contrast reference grid on the world XZ plane (y = 0)."""
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for coordinate in range(-10, 11):
            alpha = 0.30 if coordinate == 0 else 0.16
            glColor4f(0.30, 0.32, 0.34, alpha)
            glVertex3f(float(coordinate), 0.0, -10.0)
            glVertex3f(float(coordinate), 0.0, 10.0)
            glVertex3f(-10.0, 0.0, float(coordinate))
            glVertex3f(10.0, 0.0, float(coordinate))
        glEnd()

    def _draw_coordinate_frame(self):
        axis_length = 4.0
        rotated_axes = self.rotation_matrix * axis_length
        origin = tuple(map(float, self.position))
        glLineWidth(4.5)
        glBegin(GL_LINES)
        glColor3f(1.0, 0.18, 0.18)
        glVertex3f(*origin)
        glVertex3f(*map(float, self.position + rotated_axes[:, 0]))

        glColor3f(0.18, 1.0, 0.35)
        glVertex3f(*origin)
        glVertex3f(*map(float, self.position + rotated_axes[:, 1]))

        glColor3f(0.2, 0.48, 1.0)
        glVertex3f(*origin)
        glVertex3f(*map(float, self.position + rotated_axes[:, 2]))
        glEnd()


class RoboMatrixProWindow(QMainWindow):
    """Interactive dashboard for 3D rotation and rigid-body pose."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RoboMatrix 3D Pro")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(self._stylesheet())

        self._build_ui()

    def _build_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(22, 18, 22, 20)
        root_layout.setSpacing(16)
        workspace_layout = QHBoxLayout()
        workspace_layout.setSpacing(14)
        workspace_layout.addWidget(self._create_controls_panel())
        workspace_layout.addWidget(self._create_viewport_panel(), stretch=1)
        root_layout.addLayout(workspace_layout, stretch=1)
        root_layout.addWidget(self._create_telemetry_panel())
        self._update_rotation()

    def _create_controls_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(310)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)
        brand_row.addWidget(EngineeringLogo())
        brand_text = QVBoxLayout()
        brand_text.setSpacing(3)
        brand_title = QLabel("ROBOMATRIX 3D")
        brand_title.setObjectName("brandTitle")
        brand_subtitle = QLabel(
            "Project 1 of 10 | Rigid Body Kinematics"
        )
        brand_subtitle.setObjectName("appSubtitle")
        brand_subtitle.setWordWrap(True)
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_subtitle)
        brand_row.addLayout(brand_text, stretch=1)
        layout.addLayout(brand_row)
        layout.addWidget(self._create_section_title("ORIENTATION"))

        scroll_area = QScrollArea()
        scroll_area.setObjectName("controlsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_content = QWidget()
        controls_layout = QVBoxLayout(controls_content)
        controls_layout.setContentsMargins(0, 0, 4, 0)
        controls_layout.setSpacing(8)
        controls_layout.addWidget(self._create_section_title("EULER ROTATION"))

        self.rotation_sliders = {}
        self.rotation_value_labels = {}
        for axis, label_text in (
            ("roll", "ROLL  ·  X-AXIS"),
            ("pitch", "PITCH  ·  Y-AXIS"),
            ("yaw", "YAW  ·  Z-AXIS"),
        ):
            control_header = QHBoxLayout()
            axis_label = QLabel(label_text)
            axis_label.setObjectName("axisLabel")
            value_label = QLabel("0°")
            value_label.setObjectName("angleValue")
            control_header.addWidget(axis_label)
            control_header.addStretch()
            control_header.addWidget(value_label)
            controls_layout.addLayout(control_header)

            slider = QSlider(Qt.Horizontal)
            slider.setObjectName("rotationSlider")
            slider.setRange(-180, 180)
            slider.setValue(0)
            slider.setTracking(True)
            slider.setPageStep(10)
            slider.setMinimumHeight(18)
            slider.valueChanged.connect(self._update_rotation)
            self.rotation_sliders[axis] = slider
            self.rotation_value_labels[axis] = value_label
            controls_layout.addWidget(slider)

        controls_layout.addWidget(
            self._create_section_title("POSITION / TRANSLATION")
        )
        self.position_sliders = {}
        self.position_value_labels = {}
        for axis, label_text in (
            ("x", "X-AXIS"),
            ("y", "Y-AXIS"),
            ("z", "Z-AXIS"),
        ):
            control_header = QHBoxLayout()
            axis_label = QLabel(label_text)
            axis_label.setObjectName("axisLabel")
            value_label = QLabel("0.0")
            value_label.setObjectName("angleValue")
            control_header.addWidget(axis_label)
            control_header.addStretch()
            control_header.addWidget(value_label)
            controls_layout.addLayout(control_header)

            slider = QSlider(Qt.Horizontal)
            slider.setObjectName("rotationSlider")
            slider.setRange(-30, 30)
            slider.setValue(0)
            slider.setTracking(True)
            slider.setPageStep(10)
            slider.setMinimumHeight(18)
            slider.valueChanged.connect(self._update_rotation)
            self.position_sliders[axis] = slider
            self.position_value_labels[axis] = value_label
            controls_layout.addWidget(slider)

        hint = QLabel("Live rigid-body pose controls.")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        controls_layout.addWidget(hint)
        controls_layout.addStretch()
        scroll_area.setWidget(controls_content)
        layout.addWidget(scroll_area, stretch=1)

        reset_button = QPushButton("🔄 Reset Visualizer")
        reset_button.setObjectName("primaryButton")
        reset_button.setMinimumHeight(42)
        reset_button.setCursor(Qt.PointingHandCursor)
        reset_button.clicked.connect(self._reset_transform)
        layout.addWidget(reset_button)
        return panel

    def _create_viewport_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self._create_section_title("3D VIEWPORT"))
        interaction_hint = QLabel("LEFT-DRAG TO ORBIT  ·  SCROLL TO ZOOM")
        interaction_hint.setObjectName("interactionHint")
        layout.addWidget(interaction_hint)

        self.opengl_viewport = OpenGLViewport()
        layout.addWidget(self.opengl_viewport, stretch=1)
        return panel

    def _create_telemetry_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumHeight(190)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(self._create_section_title("XCODE LIVE LOGIC STREAM"))

        self.telemetry_output = QPlainTextEdit()
        self.telemetry_output.setObjectName("telemetryOutput")
        self.telemetry_output.setReadOnly(True)
        self.telemetry_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.telemetry_output.setPlaceholderText(
            "Live SE(3), exponential coordinates, and SHA-256 integrity digest."
        )
        self.telemetry_output.setPlainText(
            "SYSTEM  |  Awaiting transform data..."
        )
        telemetry_font = QFont("Consolas", 10)
        self.telemetry_output.setFont(telemetry_font)
        layout.addWidget(self.telemetry_output, stretch=1)
        return panel

    @staticmethod
    def _create_section_title(text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _reset_transform(self):
        sliders = tuple(self.rotation_sliders.values()) + tuple(
            self.position_sliders.values()
        )
        previous_signal_states = [
            slider.blockSignals(True) for slider in sliders
        ]
        try:
            for slider in sliders:
                slider.setValue(0)
        finally:
            for slider, was_blocked in zip(sliders, previous_signal_states):
                slider.blockSignals(was_blocked)
        self.opengl_viewport.reset_camera()
        self._update_rotation()

    @staticmethod
    def _rotation_matrix_from_euler(roll_degrees, pitch_degrees, yaw_degrees):
        """Build SO(3) using Rz(yaw) @ Ry(pitch) @ Rx(roll)."""
        roll, pitch, yaw = np.radians(
            [roll_degrees, pitch_degrees, yaw_degrees]
        )
        cos_roll, sin_roll = np.cos(roll), np.sin(roll)
        cos_pitch, sin_pitch = np.cos(pitch), np.sin(pitch)
        cos_yaw, sin_yaw = np.cos(yaw), np.sin(yaw)

        rotation_x = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, cos_roll, -sin_roll],
                [0.0, sin_roll, cos_roll],
            ]
        )
        rotation_y = np.array(
            [
                [cos_pitch, 0.0, sin_pitch],
                [0.0, 1.0, 0.0],
                [-sin_pitch, 0.0, cos_pitch],
            ]
        )
        rotation_z = np.array(
            [
                [cos_yaw, -sin_yaw, 0.0],
                [sin_yaw, cos_yaw, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        return rotation_z @ rotation_y @ rotation_x

    @staticmethod
    def _rotation_vector(rotation_matrix):
        """Apply Rodrigues' matrix-log formula and return axis times angle.

        The principal-axis formula uses the skew part of R away from pi.
        At identity the vector is zero; close to pi, an eigensystem recovers
        the axis because the skew part becomes numerically ill-conditioned.
        """
        cosine_theta = np.clip(
            (np.trace(rotation_matrix) - 1.0) / 2.0, -1.0, 1.0
        )
        theta = float(np.arccos(cosine_theta))

        if theta < 1e-8:
            return np.zeros(3, dtype=float)

        if np.pi - theta < 1e-6:
            symmetric_part = (rotation_matrix + np.identity(3)) / 2.0
            eigenvalues, eigenvectors = np.linalg.eigh(symmetric_part)
            axis = eigenvectors[:, np.argmax(eigenvalues)]
            axis /= np.linalg.norm(axis)
            return axis * theta

        skew_vector = np.array(
            [
                rotation_matrix[2, 1] - rotation_matrix[1, 2],
                rotation_matrix[0, 2] - rotation_matrix[2, 0],
                rotation_matrix[1, 0] - rotation_matrix[0, 1],
            ]
        )
        return (theta / (2.0 * np.sin(theta))) * skew_vector

    def _update_rotation(self):
        """Recompute pose telemetry and request a coalesced viewport repaint."""
        angles = {
            axis: slider.value()
            for axis, slider in self.rotation_sliders.items()
        }
        for axis, value in angles.items():
            self.rotation_value_labels[axis].setText(f"{value}°")

        position = np.array(
            [slider.value() / 10.0 for slider in self.position_sliders.values()],
            dtype=float,
        )
        for axis, value in zip(self.position_sliders, position):
            self.position_value_labels[axis].setText(f"{value:+.1f}")

        rotation_matrix = self._rotation_matrix_from_euler(
            angles["roll"], angles["pitch"], angles["yaw"]
        )
        # SE(3) stores rotation in the upper-left block and translation
        # in the final column, with the homogeneous bottom row [0, 0, 0, 1].
        transform = np.identity(4, dtype=float)
        transform[:3, :3] = rotation_matrix
        transform[:3, 3] = position
        rotation_vector = self._rotation_vector(rotation_matrix)
        # Hash a stable human-readable matrix representation followed by the
        # project salt; SHA-256 is a digest, not encryption or authentication.
        matrix_data = np.array2string(
            transform, precision=8, separator=", ", suppress_small=False
        )
        auth_hash = hashlib.sha256(
            (
                matrix_data
                + "Zainab_Co_Robotics_Secure"
            ).encode("utf-8")
        ).hexdigest()
        self.telemetry_output.setPlainText(
            "Xcode Live Logic Stream\n"
            "POSE  |  Z-Y-X Tait-Bryan angles (degrees)\n"
            f"  Roll  (X): {angles['roll']:>4}°\n"
            f"  Pitch (Y): {angles['pitch']:>4}°\n"
            f"  Yaw   (Z): {angles['yaw']:>4}°\n\n"
            "SE(3) HOMOGENEOUS TRANSFORM  |  T = [ R  p ; 0  1 ]\n"
            "HASH INPUT MATRIX DATA\n"
            + matrix_data
            + "\n\n"
            + "ROTATION EXPONENTIAL COORDINATES  |  omega * theta (rad)\n"
            + "  ["
            + "  ".join(f"{value: .6f}" for value in rotation_vector)
            + " ]"
            + "\n\n"
            + f"System Auth Hash: {auth_hash}"
        )
        self.opengl_viewport.set_transform(rotation_matrix, position)

    @staticmethod
    def _stylesheet():
        return """
            QWidget#centralWidget {
                background-color: #0A0A0C;
                color: #E8ECEB;
                font-family: "Segoe UI";
            }
            QFrame#panel {
                background-color: #141416;
                border: none;
                border-radius: 10px;
            }
            QLabel#brandTitle {
                color: #00FFCC;
                font-size: 19px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }
            QLabel#appSubtitle, QLabel#hintLabel {
                color: #888888;
                font-size: 10px;
            }
            QLabel#sectionTitle {
                color: #00FFCC;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 5px 0 7px;
                border-bottom: 1px solid #25272A;
            }
            QLabel#axisLabel {
                color: #C4CECC;
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#angleValue {
                color: #00FFCC;
                font-family: Consolas;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#interactionHint {
                color: #777D7B;
                font-family: Consolas;
                font-size: 9px;
                letter-spacing: 0.5px;
                padding: 0 1px 2px;
            }
            QSlider#rotationSlider {
                min-height: 22px;
            }
            QSlider#rotationSlider::groove:horizontal {
                height: 4px;
                background: #303236;
                border-radius: 2px;
            }
            QSlider#rotationSlider::sub-page:horizontal {
                background: #00BFA0;
                border-radius: 2px;
            }
            QSlider#rotationSlider::handle:horizontal {
                background: #00FFCC;
                border: 2px solid #0A0A0C;
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QPushButton#secondaryButton {
                background-color: #202124;
                color: #C9CECC;
                border: 1px solid #33363A;
                border-radius: 6px;
                padding: 9px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton#secondaryButton:hover {
                background-color: #292C30;
                border-color: #00FFCC;
                color: #ffffff;
            }
            QPushButton#primaryButton {
                background-color: #00D9AD;
                color: #081411;
                border: 1px solid #00FFCC;
                border-radius: 7px;
                padding: 10px 12px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#primaryButton:hover {
                background-color: #00FFCC;
                border-color: #66FFE0;
            }
            QPushButton#primaryButton:pressed {
                background-color: #00AA88;
                border-color: #00AA88;
            }
            QScrollArea#controlsScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea#controlsScrollArea QWidget {
                background: transparent;
            }
            QPlainTextEdit#telemetryOutput {
                background-color: #0E0F11;
                color: #B0F2DF;
                border: 1px solid #282B2E;
                border-radius: 7px;
                padding: 10px;
                font-family: Consolas;
                font-size: 10pt;
                selection-background-color: #087F70;
            }
            QPlainTextEdit#telemetryOutput:focus {
                border-color: #007F68;
            }
            QScrollBar:vertical {
                background: #111214;
                width: 7px;
                margin: 2px 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #44474B;
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00BFA0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """


def main():
    """Launch the splash and maximize the main window after five seconds."""
    gl_format = QGLFormat()
    gl_format.setSampleBuffers(True)
    gl_format.setSamples(4)
    QGLFormat.setDefaultFormat(gl_format)

    app = QApplication(sys.argv)
    window = RoboMatrixProWindow()
    splash = RoboMatrixSplashScreen()
    splash.show()

    def show_main_window():
        window.showMaximized()
        splash.finish(window)

    # Keep Qt's event loop responsive so the splash can paint and animate.
    QTimer.singleShot(5000, show_main_window)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())