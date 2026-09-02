import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components" as Components
import "../../theme" as ThemeKit

Item {
    id: root

    ThemeKit.Theme { id: theme }

    property int currentOption: 0
    property int pendingOption: 0
    property int carouselDirection: 0
    property int carouselStepDistance: 1
    property real carouselProgress: 0
    property string localStatusText: ""
    readonly property int optionCount: recoveryOptions.count
    readonly property bool carouselMoving: carouselAnimation.running

    function carouselOffset(index) {
        var offset = index - root.currentOption
        if (offset > root.optionCount / 2) {
            offset -= root.optionCount
        }
        if (offset < -root.optionCount / 2) {
            offset += root.optionCount
        }
        return offset - (root.carouselProgress * root.carouselDirection * root.carouselStepDistance)
    }

    function centerWeight(offset) {
        return Math.max(0.0, Math.min(1.0, 1.0 - Math.abs(offset)))
    }

    function edgeFade(offset) {
        return Math.max(0.0, Math.min(1.0, 1.0 - Math.max(0.0, Math.abs(offset) - 1.0) / 0.85))
    }

    function animateToOption(targetIndex) {
        if (carouselAnimation.running || targetIndex === currentOption || optionCount <= 1) {
            return
        }

        var forwardDistance = (targetIndex - currentOption + optionCount) % optionCount
        var backwardDistance = (currentOption - targetIndex + optionCount) % optionCount

        pendingOption = targetIndex
        carouselDirection = forwardDistance <= backwardDistance ? 1 : -1
        carouselStepDistance = carouselDirection > 0 ? forwardDistance : backwardDistance
        carouselProgress = 0
        localStatusText = ""
        carouselAnimation.restart()
    }

    function previousOption() {
        animateToOption((currentOption + optionCount - 1) % optionCount)
    }

    function nextOption() {
        animateToOption((currentOption + 1) % optionCount)
    }

    function previewAction() {
        if (currentOption === 0 && typeof unlockController !== "undefined" && unlockController !== null) {
            unlockController.goToRecoveryUnlock()
            return
        }
        localStatusText = recoveryOptions.get(currentOption).pendingText
    }

    NumberAnimation {
        id: carouselAnimation
        target: root
        property: "carouselProgress"
        from: 0
        to: 1
        duration: 360
        easing.type: Easing.InOutCubic
        onStopped: {
            root.currentOption = root.pendingOption
            root.carouselProgress = 0
            root.carouselDirection = 0
            root.carouselStepDistance = 1
        }
    }

    ListModel {
        id: recoveryOptions

        ListElement {
            title: "Use Recovery Codes"
            description: "Recover access with the emergency codes generated for this vault."
            actionText: "Use Recovery Codes"
            pendingText: "Recovery code entry is the next screen in this flow."
            marker: "RC"
            destructive: false
        }

        ListElement {
            title: "Restore Backup"
            description: "Replace the local vault with a backup file, then unlock it with its main password."
            actionText: "Restore Backup"
            pendingText: "Backup restore will open a file picker in the next backend slice."
            marker: "BK"
            destructive: false
        }

        ListElement {
            title: "Reset Local Vault"
            description: "Delete the local vault on this device and create a new one. This will not recover saved passwords."
            actionText: "Reset Local Vault"
            pendingText: "Reset requires a destructive confirmation screen before it runs."
            marker: "RS"
            destructive: true
        }
    }

    Image {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: -170
        anchors.bottomMargin: 58
        width: Math.min(parent.width * 0.52, 748)
        height: parent.height * 1.08
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
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.58, 840)
        color: "transparent"
        z: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(0.05, 0.05, 0.08, 0.0) }
            GradientStop { position: 0.34; color: Qt.rgba(0.05, 0.05, 0.08, 0.16) }
            GradientStop { position: 0.72; color: Qt.rgba(0.05, 0.05, 0.08, 0.42) }
            GradientStop { position: 1.0; color: Qt.rgba(0.05, 0.05, 0.08, 0.86) }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        z: 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.02, 0.02, 0.04, 0.06) }
            GradientStop { position: 0.54; color: Qt.rgba(0.02, 0.02, 0.04, 0.14) }
            GradientStop { position: 1.0; color: Qt.rgba(0.02, 0.02, 0.04, 0.48) }
        }
    }

    ColumnLayout {
        id: content
        anchors.centerIn: parent
        width: Math.min(parent.width - 56, 800)
        spacing: 22
        z: 2

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10
            opacity: 0.84

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
            Layout.preferredWidth: 560
            spacing: 10

            Text {
                Layout.fillWidth: true
                text: "Recovery Options"
                color: "#EAEAEA"
                font.family: "Georgia"
                font.pixelSize: 34
                font.weight: Font.Bold
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                Layout.fillWidth: true
                text: "Choose the local recovery path before resetting this device."
                color: "#B0B0B0"
                font.family: "Segoe UI"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }

        Item {
            id: carouselStage
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Math.min(content.width, 760)
            Layout.preferredHeight: 230
            clip: true

            Repeater {
                model: recoveryOptions

                Rectangle {
                    id: optionCard

                    readonly property real offset: root.carouselOffset(index)
                    readonly property real centerAmount: root.centerWeight(offset)
                    readonly property real fadeAmount: root.edgeFade(offset)
                    readonly property bool selected: centerAmount > 0.58

                    width: 318 + centerAmount * 122
                    height: 98 + centerAmount * 46
                    x: carouselStage.width / 2 - width / 2 + offset * 335
                    y: 64 - centerAmount * 22
                    z: 4 + Math.round(centerAmount * 8)
                    opacity: fadeAmount * (0.24 + centerAmount * 0.76)
                    scale: 0.84 + centerAmount * 0.16
                    radius: 6
                    border.width: 1
                    border.color: selected
                        ? (model.destructive ? theme.danger : theme.accentPrimary)
                        : "#3A2A40"
                    gradient: Gradient {
                        GradientStop {
                            position: 0.0
                            color: selected
                                ? (model.destructive ? Qt.rgba(0.18, 0.08, 0.10, 0.96) : Qt.rgba(0.18, 0.12, 0.20, 0.96))
                                : Qt.rgba(0.08, 0.075, 0.10, 0.74)
                        }
                        GradientStop {
                            position: 1.0
                            color: selected
                                ? (model.destructive ? Qt.rgba(0.10, 0.08, 0.10, 0.94) : Qt.rgba(0.10, 0.085, 0.13, 0.94))
                                : Qt.rgba(0.06, 0.055, 0.075, 0.70)
                        }
                    }

                    Behavior on border.color { ColorAnimation { duration: 180 } }

                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width + 30
                        height: parent.height + 28
                        radius: 12
                        color: model.destructive ? theme.danger : theme.accentPrimary
                        opacity: centerAmount * 0.14
                        z: -1
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: !root.carouselMoving
                        onClicked: root.animateToOption(index)
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: 5
                        color: "transparent"
                        border.width: selected ? 1 : 0
                        border.color: selected
                            ? (model.destructive ? Qt.rgba(0.78, 0.07, 0.12, 0.42) : Qt.rgba(0.72, 0.14, 0.40, 0.42))
                            : "transparent"
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 18 + optionCard.centerAmount * 8
                        anchors.rightMargin: 18 + optionCard.centerAmount * 10
                        anchors.topMargin: 14 + optionCard.centerAmount * 8
                        anchors.bottomMargin: 14 + optionCard.centerAmount * 8
                        spacing: 16 + optionCard.centerAmount * 4

                        Rectangle {
                            Layout.preferredWidth: 44 + optionCard.centerAmount * 18
                            Layout.preferredHeight: 44 + optionCard.centerAmount * 18
                            Layout.alignment: Qt.AlignVCenter
                            radius: 6
                            color: model.destructive
                                ? Qt.rgba(0.26, 0.05, 0.07, 0.46 + optionCard.centerAmount * 0.32)
                                : Qt.rgba(0.22, 0.13, 0.24, 0.46 + optionCard.centerAmount * 0.36)
                            border.width: 1
                            border.color: model.destructive ? theme.danger : "#6A3A70"

                            Text {
                                anchors.centerIn: parent
                                text: model.marker
                                color: model.destructive ? "#F1C0C4" : "#E7B8E7"
                                font.family: "Segoe UI"
                                font.pixelSize: 13 + optionCard.centerAmount * 4
                                font.weight: Font.DemiBold
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                Layout.fillWidth: true
                                text: model.title
                                color: model.destructive && selected ? "#F1C0C4" : (selected ? "#E7B8E7" : "#CFC6D4")
                                font.family: "Segoe UI"
                                font.pixelSize: 14 + optionCard.centerAmount * 4
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: model.description
                                color: selected ? "#D8D8E3" : "#8B8390"
                                font.family: "Segoe UI"
                                font.pixelSize: 11 + optionCard.centerAmount * 2
                                lineHeight: 1.0 + optionCard.centerAmount * 0.14
                                wrapMode: Text.WordWrap
                                maximumLineCount: selected ? 3 : 2
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Rectangle {
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.topMargin: 16
                        anchors.rightMargin: 16
                        width: 11
                        height: 11
                        radius: 6
                        color: model.destructive ? theme.danger : "#E7B8E7"
                        opacity: optionCard.centerAmount * 0.92
                    }
                }
            }

            Button {
                id: previousArrow
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 100
                width: 44
                height: 44
                z: 30
                text: "<"
                enabled: !root.carouselMoving
                onClicked: root.previousOption()
                background: Rectangle {
                    radius: 22
                    color: parent.hovered ? Qt.rgba(0.22, 0.13, 0.24, 0.94) : Qt.rgba(0.10, 0.085, 0.13, 0.78)
                    border.width: 1
                    border.color: parent.hovered ? theme.accentPrimary : "#4A204A"
                }
                contentItem: Text {
                    text: previousArrow.text
                    color: "#EAEAEA"
                    font.family: "Segoe UI"
                    font.pixelSize: 21
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Button {
                id: nextArrow
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 100
                width: 44
                height: 44
                z: 30
                text: ">"
                enabled: !root.carouselMoving
                onClicked: root.nextOption()
                background: Rectangle {
                    radius: 22
                    color: parent.hovered ? Qt.rgba(0.22, 0.13, 0.24, 0.94) : Qt.rgba(0.10, 0.085, 0.13, 0.78)
                    border.width: 1
                    border.color: parent.hovered ? theme.accentPrimary : "#4A204A"
                }
                contentItem: Text {
                    text: nextArrow.text
                    color: "#EAEAEA"
                    font.family: "Segoe UI"
                    font.pixelSize: 21
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: -6
            spacing: 13

            Repeater {
                model: recoveryOptions

                Rectangle {
                    width: index === root.currentOption ? 13 : 11
                    height: index === root.currentOption ? 13 : 11
                    radius: 7
                    color: index === root.currentOption ? "#E7B8E7" : Qt.rgba(1, 1, 1, 0.10)
                    border.width: 1
                    border.color: index === root.currentOption ? theme.accentPrimary : "#4A204A"

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        enabled: !root.carouselMoving
                        onClicked: root.animateToOption(index)
                    }
                }
            }
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 420
            text: root.localStatusText
            visible: root.localStatusText.length > 0
            color: theme.textMuted
            font.family: "Segoe UI"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
        }

        Components.PrimaryButton {
            objectName: "forgotPrimaryActionButton"
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: false
            Layout.preferredWidth: 304
            width: 304
            radius: 18
            text: recoveryOptions.get(root.currentOption).actionText
            destructive: recoveryOptions.get(root.currentOption).destructive
            onClicked: root.previewAction()
        }

        Components.TextLink {
            Layout.alignment: Qt.AlignHCenter
            text: "Back to Unlock"
            onActivated: unlockController.goToUnlock()
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
