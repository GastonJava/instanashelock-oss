import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components
import "../../theme" as ThemeKit

Item {
    id: root

    ThemeKit.Theme { id: theme }

    readonly property var controller: (typeof unlockController !== "undefined" && unlockController !== null)
        ? unlockController
        : null
    readonly property string codes: controller ? controller.recoveryCodes : ""
    readonly property var groups: codes.length > 0 ? codes.split("-") : []

    Image {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: -170
        anchors.bottomMargin: 72
        width: Math.min(parent.width * 0.52, 748)
        height: parent.height * 1.06
        source: "../../../../../assets/v2/auth/common/vault_artwork.svg"
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignRight
        verticalAlignment: Image.AlignBottom
        asynchronous: true
        smooth: true
        opacity: parent.width >= 880 ? 0.22 : 0.14
        z: 0
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        z: 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.02, 0.02, 0.04, 0.05) }
            GradientStop { position: 0.55; color: Qt.rgba(0.02, 0.02, 0.04, 0.1) }
            GradientStop { position: 1.0; color: Qt.rgba(0.02, 0.02, 0.04, 0.44) }
        }
    }

    ColumnLayout {
        id: content
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 520)
        spacing: 18
        z: 2

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Save your recovery codes"
            color: "#EAEAEA"
            font.family: "Segoe UI"
            font.pixelSize: 24
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            Layout.fillWidth: true
            text: "These codes are the local fallback for this vault. Keep them somewhere separate from this device."
            color: "#B0B0B0"
            font.family: "Segoe UI"
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Rectangle {
            Layout.fillWidth: true
            color: Qt.rgba(0.10, 0.09, 0.13, 0.86)
            border.width: 1
            border.color: "#4A204A"
            radius: theme.radiusMd
            implicitHeight: codesGrid.implicitHeight + 32

            GridLayout {
                id: codesGrid
                anchors.centerIn: parent
                columns: 2
                columnSpacing: 30
                rowSpacing: 8

                Repeater {
                    model: root.groups

                    Text {
                        text: (index + 1) + ". " + modelData
                        color: "#EAEAEA"
                        font.family: "Consolas"
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: "Do not store these codes inside the vault you just created."
            color: "#D6A4A8"
            font.family: "Segoe UI"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Components.PrimaryButton {
            objectName: "recoveryCodesAcknowledgeButton"
            Layout.fillWidth: true
            Layout.preferredWidth: 360
            Layout.alignment: Qt.AlignHCenter
            text: "I saved these codes"
            enabled: root.codes.length > 0
            onClicked: if (root.controller) root.controller.acknowledgeRecoveryCodes()
        }
    }
}
