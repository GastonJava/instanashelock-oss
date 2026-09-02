import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeKit

Control {
    id: root
    property string text: ""
    property bool underlineOnHover: true
    property bool destructive: false
    signal activated()

    ThemeKit.Theme { id: theme }

    implicitWidth: label.implicitWidth
    implicitHeight: label.implicitHeight + 4

    contentItem: Text {
        id: label
        text: root.text
        color: !root.enabled
            ? theme.textMuted
            : (hotspot.containsMouse
                ? (root.destructive ? theme.danger : theme.accentTech)
                : (root.destructive ? theme.danger : theme.textMuted))
        font.family: "Segoe UI"
        font.pixelSize: 13
        font.underline: root.enabled && root.underlineOnHover && hotspot.containsMouse
        horizontalAlignment: Text.AlignHCenter
    }

    MouseArea {
        id: hotspot
        anchors.fill: parent
        enabled: root.enabled
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: root.activated()
    }
}
