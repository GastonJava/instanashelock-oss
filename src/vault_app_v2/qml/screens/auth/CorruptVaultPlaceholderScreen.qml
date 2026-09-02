import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components
import "../../theme" as ThemeKit

Item {
    ThemeKit.Theme { id: theme }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 560)
        spacing: 16

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "This local vault looks invalid"
            font.family: "Segoe UI"
            font.pixelSize: 24
            font.bold: true
            color: theme.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            width: parent.width
            text: "Restore-from-backup and reset-device flows land in the next auth slice. v2 routes here instead of pretending the vault can still unlock safely."
            color: theme.textMuted
            font.family: "Segoe UI"
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Components.PrimaryButton {
            text: "Back to unlock"
            onClicked: unlockController.goToUnlock()
        }
    }
}
