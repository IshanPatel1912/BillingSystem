[Setup]
AppName=BillingSystem
AppVersion=1.0
DefaultDirName={pf}\BillingSystem
DefaultGroupName=BillingSystem
OutputDir=Installer
OutputBaseFilename=BillingSystem_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\BillingSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "path\to\chromedriver.exe"; DestDir: "{app}\driver"; Flags: ignoreversion

[Icons]
Name: "{group}\BillingSystem"; Filename: "{app}\BillingSystem.exe"
Name: "{commondesktop}\BillingSystem"; Filename: "{app}\BillingSystem.exe"

[Run]
Filename: "{app}\BillingSystem.exe"; Description: "Launch BillingSystem"; Flags: nowait postinstall