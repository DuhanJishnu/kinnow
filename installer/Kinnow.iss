; Inno Setup Script for Kinnow
; Creates a standard Windows installer (Kinnow-Setup.exe) with Desktop, Start Menu, and Startup options.

#define MyAppName "Kinnow"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Jishnu Duhan"
#define MyAppURL "https://github.com/DuhanJishnu/kinnow"
#define MyAppExeName "Kinnow.exe"

[Setup]
AppId={{5E28B146-59A6-4CB3-95D9-3BA5E7A2A944}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Kinnow-Setup
SetupIconFile=..\assets\kinnow.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startmenu"; Description: "Add shortcut to &Start Menu"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start Kinnow automatically when Windows &starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\Kinnow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
