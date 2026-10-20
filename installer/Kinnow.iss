; Inno Setup Script for Kinnow
; Creates a standard Windows installer (Kinnow-Setup.exe) with Desktop, Start Menu, and Startup options.

#define MyAppName "Kinnow"
#define MyAppVersion "0.2.0"
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
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=0.2.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Kinnow Setup
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion=0.2.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startmenu"; Description: "Add shortcut to &Start Menu"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start Kinnow automatically when Windows &starts"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "..\dist\Kinnow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure KillRunningKinnow();
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/f /im {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(250);
end;

function InitializeSetup(): Boolean;
begin
  KillRunningKinnow();
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  KillRunningKinnow();
  Result := True;
end;

