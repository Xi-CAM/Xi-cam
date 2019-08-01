; Note: This script must be located at a top-level above all xi-cam repos. You'll have to manually copy it one directory up.

; -------------------------------
; Start
  !include MUI2.nsh
  !include x64.nsh
  !define VERSION "2.1.1"
  !define MUI_PRODUCT "Xi-cam"
  !define MUI_FILE "Xi-cam"
  !define MUI_VERSION ""
  !define MUI_BRANDINGTEXT "Xi-cam ${VERSION}"
  CRCCheck On

  ; We should test if we must use an absolute path
  ;!include "${NSISDIR}\Contrib\Modern UI\System.nsh"


;---------------------------------
;General

  Name "Xi-cam ${VERSION}"
  OutFile "Xi-cam-${VERSION}-amd64.exe"
  ;ShowInstDetails "nevershow"
  ;ShowUninstDetails "nevershow"
  ;SetCompressor "bzip2"

  !define MUI_INSTFILESPAGE_COLORS "FFFFFF 000000" ;Two colors
  !define MUI_PAGE_HEADER_TEXT "Xi-cam ${Version} Installation:"
  !define MUI_ICON "../xi-cam.gui/xicam/gui/static/icons/xicam.ico"
  !define MUI_UNICON "../xi-cam.gui/xicam/gui/static/icons/xicam.ico"
  ;!define MUI_SPECIALBITMAP "Bitmap.bmp"


;--------------------------------
;Folder selection page

  InstallDir "$PROGRAMFILES64\${MUI_PRODUCT}"


;--------------------------------
;Modern UI Configuration

  !define MUI_WELCOMEPAGE
  !define MUI_LICENSEPAGE
  !define MUI_DIRECTORYPAGE
  !define MUI_ABORTWARNING
  !define MUI_UNINSTALLER
  !define MUI_UNCONFIRMPAGE
  !define MUI_FINISHPAGE

;  !define MUI_COMPONENTSPAGE_SMALLDESC ;No value


;--------------------------------
;Language

  !insertmacro MUI_LANGUAGE "English"


;--------------------------------
;Modern UI System

;  !insertmacro MUI_SYSTEM


;--------------------------------
;Data

  LicenseData "LICENSE.md"


;--------------------------------
;Installer Sections
Section "install"

;Add files
  SetOutPath "$INSTDIR"

  File /r ..\dist\Xi-cam\*

;create desktop shortcut
  CreateShortCut "$DESKTOP\${MUI_PRODUCT}.lnk" "$INSTDIR\${MUI_FILE}.exe" ""

;create start-menu items
  CreateDirectory "$SMPROGRAMS\${MUI_PRODUCT}"
  CreateShortCut "$SMPROGRAMS\${MUI_PRODUCT}\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
  CreateShortCut "$SMPROGRAMS\${MUI_PRODUCT}\${MUI_PRODUCT}.lnk" "$INSTDIR\${MUI_FILE}.exe" "" "$INSTDIR\${MUI_FILE}.exe" 0

;write uninstall information to the registry
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT}" "DisplayName" "${MUI_PRODUCT} (remove only)"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT}" "UninstallString" "$INSTDIR\Uninstall.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd


;--------------------------------
;Uninstaller Section
Section "Uninstall"

;Delete Files
  RMDir /r "$INSTDIR\*.*"

;Remove the installation directory
  RMDir "$INSTDIR"

;Delete Start Menu Shortcuts
  Delete "$DESKTOP\${MUI_PRODUCT}.lnk"
  Delete "$SMPROGRAMS\${MUI_PRODUCT}\*.*"
  RmDir  "$SMPROGRAMS\${MUI_PRODUCT}"

;Delete Uninstaller And Unistall Registry Entries
  DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\${MUI_PRODUCT}"
  DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\${MUI_PRODUCT}"

SectionEnd


;--------------------------------
;MessageBox Section


;Function that calls a messagebox when installation finished correctly
Function .onInstSuccess
  MessageBox MB_OK "You have successfully installed ${MUI_PRODUCT}. Use the desktop icon to start the program."
FunctionEnd

Function un.onUninstSuccess
  MessageBox MB_OK "You have successfully uninstalled ${MUI_PRODUCT}."
FunctionEnd


;eof