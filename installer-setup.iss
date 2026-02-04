; Script generated for Asana Gantt Exporter
; SAVE THIS FILE IN YOUR PROJECT ROOT FOLDER (Next to src, logos, etc.)

[Setup]
; NOTE: The value of AppId uniquely identifies this application. 
; Do not use the same AppId value in installers for other applications.
AppId={{779611BC-F2B3-4339-B9CD-232823368E0B}
AppName=Asana Gantt Exporter
AppVersion=1.0
; This displays your name in the "Add/Remove Programs" list
AppPublisher=Jens Vissenberg
DefaultDirName={autopf}\Asana Gantt Exporter
DefaultGroupName=Asana Gantt Exporter
; This is where the setup.exe will be saved (creates a folder named Output)
OutputDir=Output
OutputBaseFilename=AsanaGanttExporter-Setup
; This sets the icon for the INSTALLER file itself
; SetupIconFile=logos\Asana Gantt Exporter 3-2.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. The main executable
Source: "dist\AsanaGanttExporter\AsanaGanttExporter.exe"; DestDir: "{app}"; Flags: ignoreversion
; 2. CRITICAL: Include all other files in the folder (dependencies, dlls, etc)
Source: "dist\AsanaGanttExporter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
; Creates the shortcut in the Start Menu
Name: "{group}\Asana Gantt Exporter"; Filename: "{app}\AsanaGanttExporter.exe"
; Creates the shortcut on the Desktop (if the user checked the box)
Name: "{autodesktop}\Asana Gantt Exporter"; Filename: "{app}\AsanaGanttExporter.exe"; Tasks: desktopicon

[Run]
; Option to run the app immediately after installation finishes
Filename: "{app}\AsanaGanttExporter.exe"; Description: "{cm:LaunchProgram,Asana Gantt Exporter}"; Flags: nowait postinstall skipifsilent
