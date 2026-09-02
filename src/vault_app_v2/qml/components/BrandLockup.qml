import QtQuick
import QtQuick.Layouts
import "../theme" as ThemeKit

Item {
    id: root
    implicitWidth: content.implicitWidth
    implicitHeight: content.implicitHeight

    ThemeKit.Theme { id: theme }

    ColumnLayout {
        id: content
        anchors.centerIn: parent
        spacing: 18

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 112
            height: 112
            radius: 56
            color: "#171721"
            border.width: 1
            border.color: theme.accentTech
            opacity: 0.95

            Rectangle {
                anchors.centerIn: parent
                width: 88
                height: 88
                radius: 44
                color: Qt.rgba(184 / 255, 36 / 255, 103 / 255, 0.18)
                border.width: 1
                border.color: Qt.rgba(0, 229 / 255, 1, 0.18)
            }

            Text {
                anchors.centerIn: parent
                text: "LOCK"
                font.family: "Segoe UI"
                font.pixelSize: 20
                font.bold: true
                font.letterSpacing: 4
                color: theme.textPrimary
            }
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 6

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Instanashelock"
                font.family: "Segoe UI"
                font.pixelSize: 28
                font.bold: true
                color: theme.textPrimary
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Private local vault"
                font.family: "Consolas"
                font.pixelSize: 12
                font.letterSpacing: 1.2
                color: theme.textMuted
            }
        }
    }
}
