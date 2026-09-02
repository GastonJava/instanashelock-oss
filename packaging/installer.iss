; Inno Setup script for Instanashelock
; Compile with: iscc packaging\installer.iss

[Setup]
AppName=Instanashelock
AppVersion=1.0.0
AppPublisher=Instanashelock
AppVerName=Instanashelock 1.0.0
DefaultDirName={autopf}\Instanashelock
DefaultGroupName=Instanashelock
OutputDir=..\dist
OutputBaseFilename=Instanashelock_Setup_1.0.0
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\assets\app\instanashelock.ico
UninstallDisplayIcon={app}\instanashelock.exe
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
Source: "..\dist\instanashelock.dist\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Instanashelock"; Filename: "{app}\instanashelock.exe"
Name: "{autodesktop}\Instanashelock"; Filename: "{app}\instanashelock.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Run]
Filename: "{app}\instanashelock.exe"; Description: "Ejecutar Instanashelock"; Flags: postinstall nowait skipifsilent


