import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Window
import "components" as Components
import "screens/auth" as AuthScreens
import "theme" as ThemeKit

ApplicationWindow {
    id: appWindow
    readonly property int preferredWidth: Math.round(Screen.desktopAvailableWidth * 0.7)
    readonly property int preferredHeight: Math.round(Screen.desktopAvailableHeight * 0.9)
    width: preferredWidth
    height: preferredHeight
    x: Math.max(0, Math.round((Screen.desktopAvailableWidth - width) / 2))
    y: Math.max(0, Math.round((Screen.desktopAvailableHeight - height) / 2))
    visible: true
    title: "Instanashelock"
    color: theme.bgMain
    flags: Qt.Window | Qt.FramelessWindowHint

    ThemeKit.Theme { id: theme }

    readonly property var controller: (typeof unlockController !== "undefined" && unlockController !== null)
        ? unlockController
        : null

    function componentForRoute(routeName) {
        if (routeName === "create") {
            return createScreen
        }
        if (routeName === "forgot") {
            return forgotScreen
        }
        if (routeName === "missing") {
            return missingScreen
        }
        if (routeName === "corrupt") {
            return corruptScreen
        }
        if (routeName === "recoveryCodes") {
            return recoveryCodesScreen
        }
        if (routeName === "recoveryUnlock") {
            return recoveryUnlockScreen
        }
        if (routeName === "unlocked") {
            return unlockedScreen
        }
        return unlockScreen
    }

    function routeTo(routeName) {
        authStack.clear()
        authStack.push(componentForRoute(routeName))
    }

    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: 0
            fillGradient: RadialGradient {
                centerX: appWindow.width * 0.36
                centerY: appWindow.height * 0.42
                centerRadius: 0
                focalX: centerX
                focalY: centerY
                focalRadius: 0
                GradientStop { position: 0.0; color: "#24152A" }
                GradientStop { position: 0.38; color: "#17131D" }
                GradientStop { position: 1.0; color: theme.bgMain }
            }
            startX: 0
            startY: 0
            PathLine { x: appWindow.width; y: 0 }
            PathLine { x: appWindow.width; y: appWindow.height }
            PathLine { x: 0; y: appWindow.height }
            PathLine { x: 0; y: 0 }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.02, 0.04, 0.28)
    }

    Rectangle {
        id: titleBar
        width: parent.width
        height: 32
        color: "transparent"
        z: 100

        MouseArea {
            anchors.fill: parent
            onDoubleClicked: appWindow.visibility === Window.Maximized ? appWindow.showNormal() : appWindow.showMaximized()
            onPressed: function(mouse) {
                if (appWindow.visibility === Window.Maximized) {
                    // Start move will restore to normal size automatically in Qt occasionally
                }
                appWindow.startSystemMove()
            }
        }

        Text {
            text: "Instanashelock"
            color: "#E0E0E0"
            font.family: "Segoe UI"
            font.pixelSize: 12
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 16
        }

        Row {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 2

            Components.TopIconButton {
                width: 38
                height: 32
                iconSize: 18
                iconSource: Qt.resolvedUrl("../../../assets/v2/auth/common/help_icon.svg")
                toolTipText: "Help"
                onClicked: {}
            }

            Button {
                width: 46
                height: 32
                background: Rectangle { color: parent.hovered ? Qt.rgba(1, 1, 1, 0.1) : "transparent" }
                contentItem: Text { text: "—"; color: "#E0E0E0"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: appWindow.showMinimized()
            }
            Button {
                width: 46
                height: 32
                background: Rectangle { color: parent.hovered ? Qt.rgba(1, 1, 1, 0.1) : "transparent" }
                contentItem: Text { text: appWindow.visibility === Window.Maximized ? "❐" : "◻"; color: "#E0E0E0"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: appWindow.visibility === Window.Maximized ? appWindow.showNormal() : appWindow.showMaximized()
            }
            Button {
                width: 46
                height: 32
                background: Rectangle { color: parent.hovered ? "#E81123" : "transparent" }
                contentItem: Text { text: "✕"; color: "#E0E0E0"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: appWindow.close()
            }
        }
    }

    StackView {
        id: authStack
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
    }

    Component { id: unlockScreen; AuthScreens.UnlockScreen {} }
    Component { id: createScreen; AuthScreens.CreateVaultScreen {} }
    Component { id: forgotScreen; AuthScreens.ForgotPasswordScreen {} }
    Component { id: missingScreen; AuthScreens.MissingVaultPlaceholderScreen {} }
    Component { id: corruptScreen; AuthScreens.CorruptVaultPlaceholderScreen {} }
    Component { id: recoveryCodesScreen; AuthScreens.RecoveryCodesScreen {} }
    Component { id: recoveryUnlockScreen; AuthScreens.RecoveryUnlockScreen {} }
    Component { id: unlockedScreen; AuthScreens.UnlockedPlaceholderScreen {} }

    Connections {
        target: appWindow.controller
        function onRouteChanged(routeName) {
            appWindow.routeTo(routeName)
        }
    }

    Component.onCompleted: {
        if (appWindow.controller) {
            routeTo(appWindow.controller.initialRoute)
            appWindow.controller.syncInitialRoute()
        } else {
            routeTo("unlock")
        }
    }
}
