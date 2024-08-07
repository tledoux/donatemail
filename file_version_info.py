# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
#
# Generated from pyi-grab_version dist\GNUDB_GUI.exe
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(1, 2, 0, 0),
    prodvers=(1, 2, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('FileDescription', 'Exécutable Donatemail'),
        StringStruct('FileVersion', '1.2.0.0'),
        StringStruct('InternalName', 'donatemail'),
        StringStruct('LegalCopyright', 'Copyright © 2024 BnF'),
        StringStruct('OriginalFilename', 'Donatemail.exe'),
        StringStruct('ProductName', 'Donatemail'),
        StringStruct('ProductVersion', '1.2.0.0'),
        #StringStruct('Language', 'Language Neutral'),
        #StringStruct('Language', 'Français (France)'), => 1036  (1033 for English)
        StringStruct('LegalTrademarks', 'BnF')])
      ]), 
    VarFileInfo([VarStruct('Translation', [1036, 1200])])
  ]
)