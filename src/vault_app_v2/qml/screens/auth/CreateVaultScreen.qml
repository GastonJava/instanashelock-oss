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
    readonly property string controllerErrorText: controller ? controller.errorText : ""
    property int currentStep: 0
    property bool recoveryMode: true
    property bool passphraseHelpVisible: false
    property string localStatusText: ""
    readonly property bool passwordTooShort: createPasswordField.text.length > 0
        && createPasswordField.text.length < 12
    readonly property bool passwordMismatch: confirmPasswordField.text.length > 0
        && confirmPasswordField.text !== createPasswordField.text
    readonly property string selectedModeLabel: recoveryMode
        ? "Recovery mode selected"
        : "Strict mode selected"
    readonly property string defaultHelperText: recoveryMode
        ? "Recovery codes will be generated after the vault is created."
        : "Strict mode stores no recovery path for this vault."
    readonly property string displayStatusText: passwordMismatch
        ? "Passwords do not match."
        : (passwordTooShort
            ? "Use at least 12 characters or a longer passphrase."
            : (controllerErrorText.length > 0
                ? controllerErrorText
                : (localStatusText.length > 0 ? localStatusText : defaultHelperText)))
    readonly property bool statusIsError: passwordMismatch || passwordTooShort || controllerErrorText.length > 0

    function chooseRecoveryMode() {
        recoveryMode = true
        localStatusText = ""
    }

    function chooseStrictMode() {
        recoveryMode = false
        localStatusText = ""
    }

    function goToPasswordStep() {
        currentStep = 1
        localStatusText = ""
        createPasswordField.forceActiveFocus()
    }

    function goToModeStep() {
        currentStep = 0
        localStatusText = ""
        passphraseHelpVisible = false
    }

    function previewCreate() {
        if (!createAction.enabled) {
            shakeAnimation.restart()
            return
        }

        localStatusText = recoveryMode
            ? "Create-vault backend wiring comes next. Recovery mode is selected in this first-run shell."
            : "Create-vault backend wiring comes next. Strict mode is selected in this first-run shell."
        if (root.controller) {
            root.controller.createVault(
                createPasswordField.text,
                confirmPasswordField.text,
                root.recoveryMode
            )
        }
    }

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
            spacing: 22

            RowLayout {
                Layout.preferredHeight: 12
            }

            ColumnLayout {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 460
                spacing: 8

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Create your local vault"
                    color: "#EAEAEA"
                    font.family: "Segoe UI"
                    font.pixelSize: 24
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    Layout.fillWidth: true
                    text: root.currentStep === 0
                        ? "Choose how this vault should handle recovery before creating the main password."
                        : "Choose the main password that protects this encrypted vault."
                    color: "#B0B0B0"
                    font.family: "Segoe UI"
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 10

                Rectangle {
                    width: 118
                    height: 30
                    radius: 6
                    color: root.currentStep === 0 ? Qt.rgba(0.33, 0.09, 0.31, 0.78) : Qt.rgba(0.10, 0.09, 0.13, 0.86)
                    border.width: 1
                    border.color: root.currentStep === 0 ? theme.accentPrimary : "#4A204A"

                    Text {
                        anchors.centerIn: parent
                        text: "Protection"
                        color: root.currentStep === 0 ? "#EAEAEA" : theme.textMuted
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.goToModeStep()
                    }
                }

                Rectangle {
                    width: 28
                    height: 1
                    color: "#4A204A"
                }

                Rectangle {
                    width: 118
                    height: 30
                    radius: 6
                    color: root.currentStep === 1 ? Qt.rgba(0.33, 0.09, 0.31, 0.78) : Qt.rgba(0.10, 0.09, 0.13, 0.86)
                    border.width: 1
                    border.color: root.currentStep === 1 ? theme.accentPrimary : "#4A204A"

                    Text {
                        anchors.centerIn: parent
                        text: "Password"
                        color: root.currentStep === 1 ? "#EAEAEA" : theme.textMuted
                        font.family: "Segoe UI"
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: root.currentStep === 1
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    }
                }
            }

            StackLayout {
                id: createStack
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 420
                Layout.preferredHeight: root.currentStep === 0
                    ? protectionPage.implicitHeight
                    : passwordPage.implicitHeight
                currentIndex: root.currentStep

                Behavior on Layout.preferredHeight {
                    NumberAnimation { duration: 180 }
                }

                Item {
                    id: protectionPage
                    implicitWidth: protectionContent.implicitWidth
                    implicitHeight: protectionContent.implicitHeight

                    ColumnLayout {
                        id: protectionContent
                        anchors.centerIn: parent
                        width: 420
                        spacing: 14

                        Rectangle {
                            id: recoveryCard
                            Layout.fillWidth: true
                            color: root.recoveryMode
                                ? Qt.rgba(0.33, 0.09, 0.31, 0.78)
                                : Qt.rgba(0.10, 0.09, 0.13, 0.86)
                            border.width: 1
                            border.color: root.recoveryMode ? theme.accentPrimary : "#4A204A"
                            radius: theme.radiusMd
                            implicitHeight: recoveryCardContent.implicitHeight + 32

                            Behavior on color { ColorAnimation { duration: 180 } }
                            Behavior on border.color { ColorAnimation { duration: 180 } }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.chooseRecoveryMode()
                            }

                            ColumnLayout {
                                id: recoveryCardContent
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                Text {
                                    text: "Recovery mode"
                                    color: theme.textPrimary
                                    font.family: "Segoe UI"
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: "Generate emergency recovery codes so this vault keeps a local fallback path."
                                    color: root.recoveryMode ? "#EAEAEA" : "#A0A0A0"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        Rectangle {
                            id: strictCard
                            Layout.fillWidth: true
                            color: !root.recoveryMode
                                ? Qt.rgba(0.16, 0.05, 0.08, 0.72)
                                : Qt.rgba(0.10, 0.09, 0.13, 0.86)
                            border.width: 1
                            border.color: !root.recoveryMode ? theme.danger : "#4A204A"
                            radius: theme.radiusMd
                            implicitHeight: strictCardContent.implicitHeight + 32

                            Behavior on color { ColorAnimation { duration: 180 } }
                            Behavior on border.color { ColorAnimation { duration: 180 } }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.chooseStrictMode()
                            }

                            ColumnLayout {
                                id: strictCardContent
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8

                                Text {
                                    text: "Strict mode"
                                    color: theme.textPrimary
                                    font.family: "Segoe UI"
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: "No recovery codes are stored. If you forget the password, this vault becomes permanently unrecoverable."
                                    color: !root.recoveryMode ? "#EAEAEA" : "#A0A0A0"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root.recoveryMode
                                ? "Recommended if you want a local emergency route."
                                : "Use only if you are sure you want no recovery path."
                            color: root.recoveryMode ? theme.textMuted : "#D6A4A8"
                            font.family: "Segoe UI"
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Components.PrimaryButton {
                            id: continueAction
                            Layout.fillWidth: true
                            Layout.topMargin: 4
                            text: "Continue"
                            onClicked: root.goToPasswordStep()
                        }

                        Components.TextLink {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Return to unlock screen"
                            onActivated: if (root.controller) root.controller.goToUnlockPreview()
                        }
                    }
                }

                Item {
                    id: passwordPage
                    implicitWidth: passwordContent.implicitWidth
                    implicitHeight: passwordContent.implicitHeight

                    ColumnLayout {
                        id: passwordContent
                        anchors.centerIn: parent
                        width: 360
                        spacing: 16

                        Item {
                            id: fieldShakeWrap
                            Layout.fillWidth: true
                            implicitHeight: createPasswordField.implicitHeight
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
                                id: createPasswordField
                                objectName: "createVaultPasswordField"
                                anchors.fill: parent
                                x: fieldShakeWrap.shakeOffset
                                placeholderText: "Main password"
                                errorState: root.statusIsError
                                onTextChanged: root.localStatusText = ""
                                onAccepted: confirmPasswordField.forceActiveFocus()
                                Component.onCompleted: forceActiveFocus()
                            }
                        }

                        Components.PasswordField {
                            id: confirmPasswordField
                            objectName: "createVaultConfirmPasswordField"
                            Layout.fillWidth: true
                            placeholderText: "Confirm main password"
                            errorState: root.statusIsError
                            onTextChanged: root.localStatusText = ""
                            onAccepted: root.previewCreate()
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                Layout.fillWidth: true
                                text: "Use a long passphrase you can remember. Example: luna-cafe-rio-89"
                                color: "#B0B0B0"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }

                            Components.TextLink {
                                Layout.alignment: Qt.AlignLeft
                                text: root.passphraseHelpVisible ? "Hide passphrase tip" : "What is a passphrase?"
                                onActivated: root.passphraseHelpVisible = !root.passphraseHelpVisible
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                visible: root.passphraseHelpVisible
                                color: Qt.rgba(0.10, 0.09, 0.13, 0.84)
                                border.width: 1
                                border.color: "#4A204A"
                                radius: theme.radiusMd
                                implicitHeight: passphraseHelpText.implicitHeight + 24

                                Text {
                                    id: passphraseHelpText
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    text: "A passphrase is a longer password made from words you can recall easily. It is usually easier to remember and safer than a short password."
                                    color: "#D8D8E3"
                                    font.family: "Segoe UI"
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            implicitHeight: helperTextBlock.implicitHeight + 4

                            Text {
                                anchors.fill: parent
                                anchors.leftMargin: 1
                                anchors.topMargin: 2
                                text: root.displayStatusText
                                color: root.statusIsError
                                    ? Qt.rgba(0.05, 0.0, 0.0, 0.92)
                                    : Qt.rgba(0.0, 0.0, 0.0, 0.78)
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.weight: Font.Medium
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }

                            Text {
                                id: helperTextBlock
                                anchors.fill: parent
                                text: root.displayStatusText
                                color: root.statusIsError ? theme.bone : "#D8D8E3"
                                font.family: "Segoe UI"
                                font.pixelSize: 12
                                font.weight: Font.Medium
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }

                        Components.PrimaryButton {
                            id: createAction
                            objectName: "createVaultPrimaryButton"
                            Layout.fillWidth: true
                            text: root.controller && root.controller.busy ? "Creating..." : "Create vault"
                            enabled: createPasswordField.text.length > 0
                                && confirmPasswordField.text.length > 0
                                && !root.passwordTooShort
                                && !root.passwordMismatch
                                && (!root.controller || !root.controller.busy)
                            onClicked: root.previewCreate()
                        }

                        RowLayout {
                            Layout.alignment: Qt.AlignHCenter
                            spacing: 18

                            Components.TextLink {
                                text: "Back to protection"
                                onActivated: root.goToModeStep()
                            }

                            Components.TextLink {
                                text: root.selectedModeLabel
                                enabled: false
                                underlineOnHover: false
                            }
                        }
                    }
                }
            }
        }
    }

    RowLayout {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: 32
        anchors.bottomMargin: 32
        spacing: 10
        z: 2
        opacity: 0.72

        Image {
            Layout.preferredWidth: 30
            Layout.preferredHeight: 30
            source: "../../../../../assets/app/instanashelock_icon.svg"
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        Text {
            text: "Instanashelock"
            color: "#D8D8E3"
            font.family: "Segoe UI"
            font.pixelSize: 13
            font.weight: Font.Medium
            Layout.alignment: Qt.AlignVCenter
        }
    }

    Connections {
        target: root.controller
        function onShakeRequested() {
            shakeAnimation.restart()
        }
    }
}
