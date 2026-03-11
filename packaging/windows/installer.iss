#define MyAppName "1-Click-KB-Switch"
#define MyAppVersion GetEnv("APP_VERSION")
#define MyAppPublisher "Develastic"
#define MyAppURL "https://develastic.com"
#define MyAppExeName "1-click-kb-switch.exe"

[Setup]
AppId={{1D7CE10C-6FF1-4FE2-9B86-A166803E18AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\1-Click-KB-Switch
DefaultGroupName=1-Click-KB-Switch
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
LicenseFile=eula.txt
OutputDir=..\..\output
OutputBaseFilename=1-click-kb-switch-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\..\dist-windows\1-click-kb-switch\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\1-Click-KB-Switch"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall 1-Click-KB-Switch"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch 1-Click-KB-Switch"; Flags: nowait postinstall skipifsilent
