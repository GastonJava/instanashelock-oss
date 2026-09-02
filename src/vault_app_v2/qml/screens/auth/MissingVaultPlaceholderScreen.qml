import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components
import "../../theme" as ThemeKit

Item {
    ThemeKit.Theme { id: theme }

    readonly property var controller: (typeof unlockController !== "undefined" && unlockController !== null)
        ? unlockController
        : null

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 520)
        spacing: 16

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "No local vault yet"
            font.family: "Segoe UI"
            font.pixelSize: 24
            font.bold: true
            color: theme.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            width: parent.width
            text: "This route is kept as a fallback. New first-run flow now starts on the create-vault screen."
            color: theme.textMuted
            font.family: "Segoe UI"
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Components.PrimaryButton {
            text: "Go to create vault"
            onClicked: if (root.controller) root.controller.goToCreateVault()
        }
    }
}
