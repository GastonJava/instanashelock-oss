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
    readonly property string defaultHelperText: "The vault is locked. Enter your main password."
    readonly property string displayErrorText: controller ? controller.errorText : ""
    readonly property string displayHelperText: controller ? controller.helperText : defaultHelperText
    readonly property bool hasStatusText: displayErrorText.length > 0 || displayHelperText !== defaultHelperText

    Image {
        id: backgroundFigure
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
        opacity: parent.width >= 880 ? 0.29 : 0.18
        z: 0
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.58, 840)
        color: "transparent"
        z: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(0.05, 0.05, 0.08, 0.0) }
            GradientStop { position: 0.32; color: Qt.rgba(0.05, 0.05, 0.08, 0.14) }
            GradientStop { position: 0.68; color: Qt.rgba(0.05, 0.05, 0.08, 0.36) }
            GradientStop { position: 1.0; color: Qt.rgba(0.05, 0.05, 0.08, 0.84) }
        }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.44, 640)
        height: Math.min(parent.height * 0.7, 520)
        color: "transparent"
        z: 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.12, 0.12, 0.16, 0.0) }
            GradientStop { position: 0.58; color: Qt.rgba(0.12, 0.12, 0.16, 0.12) }
            GradientStop { position: 1.0; color: Qt.rgba(0.12, 0.12, 0.16, 0.3) }
        }
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

    Item {
        id: centerWrap
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 600)
        height: content.implicitHeight
        opacity: 0
        y: 18
        z: 2

        SequentialAnimation {
            running: true
            ParallelAnimation {
                NumberAnimation { target: centerWrap; property: "opacity"; from: 0; to: 1; duration: 260 }
                NumberAnimation { target: centerWrap; property: "y"; from: 18; to: 0; duration: 260 }
            }
        }

        ColumnLayout {
            id: content
            anchors.centerIn: parent
            width: parent.width
            spacing: 24

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 16

                Image {
                    Layout.preferredWidth: 98
                    Layout.preferredHeight: 98
                    Layout.alignment: Qt.AlignVCenter
                    source: "../../../../../assets/app/instanashelock_icon.svg"
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    text: "Instanashelock"
                    font.family: "Segoe UI"
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    color: "#EAEAEA"
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 420
                text: "The vault is locked. Enter your main password."
                font.family: "Segoe UI"
                font.pixelSize: 14
                color: "#B0B0B0"
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            Item {
                id: fieldShakeWrap
                Layout.fillWidth: false
                Layout.preferredWidth: 340
                Layout.alignment: Qt.AlignHCenter
                implicitHeight: passwordField.implicitHeight
                property real shakeOffset: 0

                SequentialAnimation {
                    id: shakeAnimation
                    NumberAnimation { target: fieldShakeWrap; property: "shakeOffset"; to: -8; duration: 36 }
                    NumberAnimation { target: fieldShakeWrap; property: "shakeOffset"; to: 8; duration: 72 }
                    NumberAnimation { target: fieldShakeWrap; property: "shakeOffset"; to: -6; duration: 48 }
                    NumberAnimation { target: fieldShakeWrap; property: "shakeOffset"; to: 6; duration: 48 }
                    NumberAnimation { target: fieldShakeWrap; property: "shakeOffset"; to: 0; duration: 36 }
                }

                Components.PasswordField {
                    id: passwordField
                    objectName: "unlockPasswordField"
                    anchors.fill: parent
                    x: fieldShakeWrap.shakeOffset
                    enabled: root.controller ? root.controller.canSubmit : false
                    errorState: root.displayErrorText.length > 0
                    placeholderText: "Main password"
                    onAccepted: if (root.controller) root.controller.submitPassword(text)
                    Component.onCompleted: forceActiveFocus()
                }
            }

            Item {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 380
                implicitHeight: helperTextBlock.visible ? helperTextBlock.implicitHeight + 4 : 0
                visible: helperTextBlock.visible

                Text {
                    anchors.fill: parent
                    anchors.leftMargin: 1
                    anchors.topMargin: 2
                    text: root.displayErrorText.length > 0 ? root.displayErrorText : root.displayHelperText
                    color: root.displayErrorText.length > 0
                        ? Qt.rgba(0.05, 0.0, 0.0, 0.92)
                        : Qt.rgba(0.0, 0.0, 0.0, 0.78)
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    visible: helperTextBlock.visible
                }

                Text {
                    id: helperTextBlock
                    anchors.fill: parent
                    text: root.displayErrorText.length > 0 ? root.displayErrorText : root.displayHelperText
                    color: root.displayErrorText.length > 0 ? theme.bone : "#D8D8E3"
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    visible: root.hasStatusText
                }
            }

            Components.PrimaryButton {
                objectName: "unlockPrimaryButton"
                text: root.controller && root.controller.busy ? "Unlocking..." : "🔒 Unlock"
                enabled: root.controller ? root.controller.canSubmit : false
                Layout.fillWidth: false
                Layout.preferredWidth: 340
                Layout.alignment: Qt.AlignHCenter
                onClicked: if (root.controller) root.controller.submitPassword(passwordField.text)
            }

            ColumnLayout {
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 8
                spacing: 16

                Components.TextLink {
                    text: "Unlock with Windows Hello"
                    enabled: false
                }

                Components.TextLink {
                    text: "Forgot your main password?"
                    onActivated: if (root.controller) root.controller.goToForgotPassword()
                }
            }
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
        z: 2
        onClicked: {}
    }

    Connections {
        target: root.controller
        function onShakeRequested() {
            shakeAnimation.restart()
        }
    }
}
