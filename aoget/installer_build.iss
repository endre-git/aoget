; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "AOGet Beta"
#define MyAppVersion "0.9.1"
#define MyAppPublisher "kosaendre"
#define MyAppURL "https://github.com/endre-git/aoget"
#define MyAppExeName "aoget.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{906E7914-F252-4DF4-A943-2A2D06EDC418}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=C:\dev\aoget_git\aoget\LICENSE
InfoBeforeFile=C:\dev\aoget_git\aoget\aoget\docs\PRE_INSTALL
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
OutputBaseFilename=aoget
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\dev\aoget_git\aoget\aoget\dist\aoget\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\dev\aoget_git\aoget\aoget\dist\aoget\config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\dev\aoget_git\aoget\aoget\dist\aoget\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\dev\aoget_git\aoget\aoget\dist\aoget\aoget\*"; DestDir: "{app}\aoget"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\dev\aoget_git\aoget\aoget\dist\aoget\settings"; DestDir: "{app}\settings"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

