import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeKit

Button {
    id: root
    property string glyph: ""
    property url iconSource: ""
    property string toolTipText: ""
    property int iconSize: 18

    ThemeKit.Theme { id: theme }

    implicitWidth: 38
    implicitHeight: 38
    hoverEnabled: true

    ToolTip.visible: hovered && toolTipText.length > 0
    ToolTip.delay: 300
    ToolTip.text: toolTipText

    contentItem: Item {
        anchors.fill: parent

        Image {
            visible: root.iconSource !== ""
            anchors.centerIn: parent
            width: root.iconSize
            height: root.iconSize
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
            asynchronous: true
            opacity: root.enabled ? (root.hovered ? 1.0 : 0.78) : 0.34
        }

        Text {
            visible: root.iconSource === ""
            anchors.fill: parent
            text: root.glyph
            color: root.hovered ? theme.textPrimary : theme.textMuted
            font.family: "Segoe UI Symbol"
            font.pixelSize: root.iconSize
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    background: Rectangle {
        radius: theme.radiusSm
        color: root.hovered ? Qt.rgba(1, 1, 1, 0.05) : "transparent"
        border.width: 1
        border.color: root.hovered ? theme.panelBorder : "transparent"

        Behavior on color {
            ColorAnimation { duration: 200 }
        }
    }
}

