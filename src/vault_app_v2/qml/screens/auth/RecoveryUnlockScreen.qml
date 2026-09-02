import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components
import "../../theme" as ThemeKit

Item {
    id: root

    ThemeKit.Theme { id: theme }

    property string localStatusText: ""

    readonly property bool hasCode: codeInput.text.trim().length > 0
    Image {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: -115
        anchors.bottomMargin: 8
        width: Math.min(parent.width * 0.48, 690)
        height: parent.height * 1.05
        source: "../../../../../assets/v2/auth/common/vault_artwork.svg"
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignRight
        verticalAlignment: Image.AlignBottom
        asynchronous: true
        smooth: true
        opacity: parent.width >= 880 ? 0.19 : 0.12
        z: 0
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        z: 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.015, 0.015, 0.025, 0.08) }
            GradientStop { position: 0.44; color: Qt.rgba(0.015, 0.015, 0.025, 0.18) }
            GradientStop { position: 1.0; color: Qt.rgba(0.015, 0.015, 0.025, 0.58) }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.0, 0.0, 0.0, 0.08)
        z: 1
    }

    ColumnLayout {
        id: content
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 720)
        spacing: 19
        z: 2

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10
            opacity: 0.82

            Image {
                Layout.preferredWidth: 46
                Layout.preferredHeight: 46
                Layout.alignment: Qt.AlignVCenter
                source: "../../../../../assets/app/instanashelock_icon.svg"
                fillMode: Image.PreserveAspectFit
                smooth: true
            }

            Text {
                text: "Instanashelock"
                color: "#DCD8DE"
                font.family: "Segoe UI"
                font.pixelSize: 22
                font.weight: Font.Medium
                Layout.alignment: Qt.AlignVCenter
            }
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Math.min(content.width, 660)
            spacing: 11

            Text {
                Layout.fillWidth: true
                text: "Use Recovery Code"
                color: "#F1EEF1"
                font.family: "Georgia"
                font.pixelSize: 44
                font.weight: Font.Bold
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                text: "Enter one recovery code generated for this local vault."
                color: "#BAB4BE"
                font.family: "Segoe UI"
                font.pixelSize: 15
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 70
            Layout.preferredWidth: Math.min(content.width, 520)
            Layout.preferredHeight: 72
            radius: 8
            color: Qt.rgba(0.08, 0.075, 0.10, 0.72)
            border.width: 1
            border.color: codeInput.activeFocus ? "#B84EC4" : "#332638"

            Behavior on border.color { ColorAnimation { duration: 160 } }

            TextField {
                id: codeInput
                objectName: "recoveryUnlockCodeInput"
                anchors.fill: parent
                anchors.leftMargin: 28
                anchors.rightMargin: 28
                horizontalAlignment: TextInput.AlignHCenter
                verticalAlignment: TextInput.AlignVCenter
                placeholderText: "PASTE RECOVERY CODE"
                placeholderTextColor: "#78707C"
                color: "#EAEAEA"
                selectedTextColor: "#FFFFFF"
                selectionColor: Qt.rgba(0.72, 0.14, 0.40, 0.58)
                font.family: "Consolas"
                font.pixelSize: 18
                font.letterSpacing: 2
                echoMode: TextInput.Password
                background: Item {}
                onTextChanged: root.localStatusText = ""
            }
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 540
            Layout.topMargin: 16
            text: "Recover access with the emergency codes generated for this local vault."
            color: "#C7C0CA"
            font.family: "Segoe UI"
            font.pixelSize: 15
            lineHeight: 1.08
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 540
            text: "Recovery only works if codes were enabled when this vault was created."
            color: "#AFA7B5"
            font.family: "Segoe UI"
            font.pixelSize: 13
            lineHeight: 1.08
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 480
            text: root.localStatusText
            visible: root.localStatusText.length > 0
            color: "#D6A4A8"
            font.family: "Segoe UI"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Button {
            id: unlockCodeButton
            objectName: "recoveryUnlockActionButton"
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: root.localStatusText.length > 0 ? 6 : 18
            Layout.preferredWidth: 600
            Layout.preferredHeight: 80
            enabled: root.hasCode
            hoverEnabled: true
            onClicked: root.localStatusText = "Recovery unlock backend will connect in the next slice."

            background: Rectangle {
                radius: 18
                border.width: 2
                border.color: !unlockCodeButton.enabled
                    ? "#414754"
                    : (unlockCodeButton.down || unlockCodeButton.hovered ? "#75E6D1" : "#7B8CFF")
                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: !unlockCodeButton.enabled
                            ? "#242936"
                            : (unlockCodeButton.down || unlockCodeButton.hovered ? "#3C3565" : "#252D48")
                    }
                    GradientStop {
                        position: 1.0
                        color: !unlockCodeButton.enabled
                            ? "#171B24"
                            : (unlockCodeButton.down || unlockCodeButton.hovered ? "#242A49" : "#171C30")
                    }
                }
                Behavior on border.color { ColorAnimation { duration: 140 } }
            }

            contentItem: Text {
                text: unlockCodeButton.text
                color: unlockCodeButton.enabled ? "#F7F0F8" : "#C8C3C9"
                font.family: "Georgia"
                font.pixelSize: 26
                font.weight: Font.Bold
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                anchors.verticalCenterOffset: 2
                style: Text.Raised
                styleColor: Qt.rgba(0.0, 0.0, 0.0, 0.58)
            }

            text: "Unlock with Code"
        }

        Components.TextLink {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: -8
            text: "Back to Recovery Options"
            onActivated: unlockController.goToForgotPassword()
        }
    }

    Components.TopIconButton {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.bottomMargin: 32
        anchors.leftMargin: 32
        width: 46
        height: 46
        iconSize: 24
        iconSource: Qt.resolvedUrl("../../../../../assets/v2/auth/common/settings_icon.svg")
        toolTipText: "Settings"
        z: 3
        onClicked: {}
    }
}
