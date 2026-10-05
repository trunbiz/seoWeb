[Setup]
AppId=SeoWeb.Desktop
AppName=ZizaSeo
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\ZizaSeo
DefaultGroupName=ZizaSeo
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=ZizaSeo-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\zizaseo.ico
UninstallDisplayIcon={app}\ZizaSeo.exe
CloseApplications=yes

[Files]
Source: "..\dist\ZizaSeo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ZizaSeo"; Filename: "{app}\ZizaSeo.exe"
Name: "{autodesktop}\ZizaSeo"; Filename: "{app}\ZizaSeo.exe"

[Run]
Filename: "{app}\ZizaSeo.exe"; Description: "Open ZizaSeo"; Flags: nowait postinstall skipifsilent
