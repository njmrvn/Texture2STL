; ============================================================================
;  Texture STL Tool — Inno Setup Installer Script
; ============================================================================
;
;  This script packages the PyInstaller one-folder output into a professional
;  Windows installer.
;
;  Prerequisites:
;    1. PyInstaller build completed:  build.bat
;       Output in:  dist\TextureSTLTool\TextureSTLTool.exe
;    2. Inno Setup 6 installed:  https://jrsoftware.org/isinfo.php
;
;  Compile:
;    - GUI:   Open this file in Inno Setup Compiler → Build → Compile
;    - CLI:   iscc.exe TextureSTLTool.iss
;
;  Output:
;    release\TextureSTLTool_Setup_1.0.0.exe
;
; ============================================================================

; ---------------------------------------------------------------------------
;  VERSION — Update these for each release
; ---------------------------------------------------------------------------
#define MyAppName        "Texture STL Tool"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "Texture STL Tool Project"
#define MyAppURL         "https://github.com/your-org/texture-stl-tool"
#define MyAppExeName     "TextureSTLTool.exe"
#define MyAppCopyright   "Copyright (C) 2026 Texture STL Tool Project"

; Paths relative to this .iss file
#define ProjectRoot      ".."
#define DistDir          ProjectRoot + "\dist\TextureSTLTool"

; Optional icon — used for installer wizard, shortcuts, and Add/Remove Programs.
; If icon.ico does not exist, comment out SetupIconFile and UninstallDisplayIcon
; lines, or remove the icon references below.
#define IconExists        FileExists(ProjectRoot + "\icon.ico")

; ============================================================================
;  [Setup] — Core installer configuration
; ============================================================================
[Setup]
; NOTE: This AppId GUID uniquely identifies this application.
; Do NOT change it between versions — Inno uses it to detect upgrades.
; Generated once. If you fork the project, generate a new GUID.
AppId={{B7E3F1A2-4D8C-4F6A-9B2E-1C5D7A3F8E90}

AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}

; Install location
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Don't allow install to a network drive
AllowNetworkDrive=no

; Allow per-user install (no admin needed) or system-wide with elevation.
; {autopf} automatically picks per-user or per-machine based on privileges.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Installer output
OutputDir={#ProjectRoot}\release
OutputBaseFilename=TextureSTLTool_Setup_{#MyAppVersion}

; Compression — lzma2/max balances size and memory usage.
; NOTE: ultra64 can cause "out of memory" errors on large VTK bundles.
Compression=lzma2/max
SolidCompression=yes
LZMANumBlockThreads=2

; Wizard appearance
WizardStyle=modern
WizardSizePercent=110,110
ShowLanguageDialog=auto

; Uninstall
Uninstallable=yes
UninstallDisplayName={#MyAppName}

; Version info embedded in the installer .exe
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoCopyright={#MyAppCopyright}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Require Windows 10 or later
MinVersion=10.0

; 64-bit only (VTK/PyVista require x64)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Prevent running while already installed version is open
AppMutex=TextureSTLToolMutex

; --- Icon setup (conditional) ---
; If you have icon.ico in the project root, these lines use it.
; If you don't have one yet, Inno will use its default icon — that's fine.
#if IconExists
SetupIconFile={#ProjectRoot}\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
#endif

; ============================================================================
;  [Languages]
; ============================================================================
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ============================================================================
;  [Tasks] — Optional choices shown to the user during install
; ============================================================================
[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

; ============================================================================
;  [Files] — What gets installed
; ============================================================================
;
;  We recursively include EVERYTHING from the PyInstaller dist folder.
;  This captures the .exe, all DLLs, Qt plugins, VTK resources, _internal/,
;  bundled textures, library data, and any other files PyInstaller produced.
;
;  IMPORTANT: Do not cherry-pick files from dist — PyInstaller's output is
;  tightly coupled and missing a single DLL can cause a crash.
;
[Files]
; Entire PyInstaller output — recursive, preserving subfolder structure
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Optional: include license and readme at the install root
Source: "{#ProjectRoot}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#ProjectRoot}\README.md";   DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Optional: icon file for use by shortcuts (if not already embedded in .exe)
Source: "{#ProjectRoot}\icon.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; ============================================================================
;  [Icons] — Shortcuts
; ============================================================================
[Icons]
; Start Menu shortcut (always created)
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; Comment: "Launch {#MyAppName}"
Name: "{group}\Uninstall {#MyAppName}";  Filename: "{uninstallexe}"

; Desktop shortcut (only if user checked the box)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Launch {#MyAppName}"

; ============================================================================
;  [Run] — Post-install actions
; ============================================================================
[Run]
; "Launch Texture STL Tool" checkbox on the final wizard page
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked

; ============================================================================
;  [UninstallDelete] — Extra cleanup on uninstall
; ============================================================================
;
;  The main install directory is removed automatically by Inno Setup.
;  We explicitly list files/folders that the app might create at runtime
;  INSIDE the install directory (e.g., logs, temp files, __pycache__).
;
;  NOTE: We do NOT delete %APPDATA%\TextureSTLTool here. That contains
;  user data (config, imported textures, library). Deleting it would
;  destroy the user's work. If you want to offer that option, use the
;  [Code] section below.
;
[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"

; ============================================================================
;  [Code] — Pascal Script for custom behavior
; ============================================================================
[Code]

// ---------------------------------------------------------------------------
//  Ask user whether to remove their personal data during uninstall
// ---------------------------------------------------------------------------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataPath: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    UserDataPath := ExpandConstant('{userappdata}\TextureSTLTool');
    if DirExists(UserDataPath) then
    begin
      if MsgBox(
        'Do you want to remove your personal Texture STL Tool data?' + #13#10 +
        '(config, texture library, imported textures)' + #13#10 + #13#10 +
        'Location: ' + UserDataPath + #13#10 + #13#10 +
        'Click "No" to keep your data for future installs.',
        mbConfirmation, MB_YESNO or MB_DEFBUTTON2
      ) = IDYES then
      begin
        DelTree(UserDataPath, True, True, True);
      end;
    end;
  end;
end;

// ---------------------------------------------------------------------------
//  Warn user if the app is currently running
// ---------------------------------------------------------------------------
function InitializeSetup(): Boolean;
begin
  Result := True;
  // The AppMutex directive already handles this, but we add a friendly message
end;

function InitializeUninstall(): Boolean;
var
  Msg: String;
begin
  Result := True;
  Msg := 'Please close Texture STL Tool before uninstalling.';
  if CheckForMutexes('TextureSTLToolMutex') then
  begin
    MsgBox(Msg, mbError, MB_OK);
    Result := False;
  end;
end;
