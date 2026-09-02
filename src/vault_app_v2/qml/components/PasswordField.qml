import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeKit

TextField {
    id: root
    property bool errorState: false
    property string helperText: ""
    property color accentColor: theme.accentPrimary

    ThemeKit.Theme { id: theme }

    Layout.fillWidth: true
    Layout.preferredWidth: theme.panelWidth
    implicitHeight: 56
    color: theme.textPrimary
    selectionColor: theme.accentPrimary
    selectedTextColor: theme.textPrimary
    echoMode: TextInput.Password
    placeholderTextColor: theme.textMuted
    font.family: "Consolas"
    font.pixelSize: 15
    leftPadding: 16
    rightPadding: 16
    topPadding: 16
    bottomPadding: 16

    background: Rectangle {
        radius: 6
        color: "#1E1A22"
        border.width: 1
        border.color: root.errorState
            ? theme.danger
            : (root.activeFocus ? "#8A3A8A" : "#4A204A")

        Behavior on border.color {
            ColorAnimation { duration: 180 }
        }
    }
}
