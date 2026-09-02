import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components
import "../../theme" as ThemeKit

Item {
    ThemeKit.Theme { id: theme }

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 520)
        spacing: 16

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Vault unlocked"
            font.family: "Segoe UI"
            font.pixelSize: 24
            font.bold: true
            color: theme.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            width: parent.width
            text: "The logged-in v2 shell is intentionally deferred. This confirms the v2 auth flow reached an unlocked session."
            color: theme.textMuted
            font.family: "Segoe UI"
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Components.PrimaryButton {
            text: "Return to unlock"
            onClicked: unlockController.goToUnlock()
        }
    }
}
