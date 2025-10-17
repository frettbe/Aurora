; Aurora Installer Script pour Inno Setup

[Setup]
AppName=Aurora
AppVersion=1.0.0
AppPublisher=6f4Software
AppPublisherURL=https://www.6f4.be/aurora/
DefaultDirName={autopf}\6f4Software\Aurora
DefaultGroupName=Aurora
OutputDir=installer_output
OutputBaseFilename=AuroraSetup-v1.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=libapp\resources\icons\app\aurora.ico
UninstallDisplayIcon={app}\AuroraAE.exe
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\AuroraAE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Aurora"; Filename: "{app}\AuroraAE.exe"
Name: "{group}\{cm:UninstallProgram,Aurora}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Aurora"; Filename: "{app}\AuroraAE.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Aurora"; Filename: "{app}\AuroraAE.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\AuroraAE.exe"; Description: "{cm:LaunchProgram,Aurora}"; Flags: nowait postinstall skipifsilent
