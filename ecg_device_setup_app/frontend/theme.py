"""Tema visual centralizado do aplicativo."""

APP_STYLESHEET = """
QWidget {
    font-family: "Segoe UI";
    font-size: 14px;
    color: #172033;
}
QMainWindow, QWidget#AppRoot {
    background: #f4f6fa;
}
QFrame#Sidebar {
    background: #111827;
    border: none;
}
QLabel#BrandTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
}
QLabel#BrandSubtitle {
    color: #9ca3af;
    font-size: 12px;
}
QFrame#ContentCard, QFrame#Panel, QFrame#StatusCard, QFrame#DeviceCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QLabel#PageTitle {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
}
QLabel#PageSubtitle, QLabel#MutedLabel {
    color: #64748b;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
}
QLineEdit {
    min-height: 38px;
    padding: 0 11px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    selection-background-color: #2563eb;
}
QLineEdit:focus {
    border: 2px solid #2563eb;
}
QLineEdit[error="true"] {
    border: 2px solid #dc2626;
}
QPushButton {
    min-height: 38px;
    padding: 0 18px;
    border-radius: 7px;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    font-weight: 600;
}
QPushButton:hover {
    background: #f8fafc;
}
QPushButton:disabled {
    color: #94a3b8;
    background: #f1f5f9;
}
QPushButton#PrimaryButton {
    color: #ffffff;
    background: #2563eb;
    border: 1px solid #2563eb;
}
QPushButton#PrimaryButton:hover {
    background: #1d4ed8;
}
QPushButton#DangerButton {
    color: #b91c1c;
}
QPushButton#InlineButton {
    min-height: 30px;
    padding: 0 10px;
}
QCheckBox {
    spacing: 9px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
QProgressBar {
    min-height: 8px;
    max-height: 8px;
    border: none;
    border-radius: 4px;
    background: #e2e8f0;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
    background: #2563eb;
}
QTextEdit, QPlainTextEdit {
    background: #0f172a;
    color: #dbeafe;
    border: none;
    border-radius: 8px;
    font-family: "Cascadia Mono", "Consolas";
    font-size: 12px;
    padding: 8px;
}
QScrollArea {
    border: none;
    background: transparent;
}
"""
