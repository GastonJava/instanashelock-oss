import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeKit

Button {
    id: root
    property color idleColor: theme.bgField
    property color hoverColor: theme.accentPrimary
    property color borderIdleColor: theme.panelBorder
    property color borderHoverColor: theme.accentPrimary
    property color textIdleColor: theme.textPrimary
    property color textHoverColor: theme.textPrimary
    property bool destructive: false
    property int radius: 6

    ThemeKit.Theme { id: theme }

    Layout.fillWidth: true
    Layout.preferredWidth: theme.panelWidth
    implicitHeight: 52
    hoverEnabled: true

    contentItem: Text {
        text: root.text
        color: root.enabled ? (root.hovered ? root.textHoverColor : root.textIdleColor) : theme.textMuted
        font.family: "Segoe UI"
        font.pixelSize: 15
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: root.radius
        color: root.enabled
            ? (root.destructive
                ? (root.hovered ? "#8E1723" : "#4A1016")
                : (root.hovered ? "#6A1B6A" : "#4A104A"))
            : "#121219"
        border.width: 1
        border.color: root.enabled
            ? (root.destructive
                ? (root.hovered ? "#D04752" : theme.danger)
                : (root.hovered ? "#9A4A9A" : "#7A3A7A"))
            : theme.panelBorder

        Behavior on color {
            ColorAnimation { duration: 200 }
        }

        Behavior on border.color {
            ColorAnimation { duration: 200 }
        }
    }
}
