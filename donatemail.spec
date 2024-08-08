# -*- mode: python -*-

block_cipher = None


a = Analysis(['donate_gui.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False,
            )

a.datas += [('images/email_gui.ico','./images/email_gui.ico', "DATA")]
a.datas += [('images/Gartoon_actions_ark_addfile_32.png','./images/Gartoon_actions_ark_addfile_32.png', "DATA")]
a.datas += [('images/Gartoon_actions_editcopy_32.png','./images/Gartoon_actions_editcopy_32.png', "DATA")]
a.datas += [('images/Gartoon_actions_exit_32.png','./images/Gartoon_actions_exit_32.png', "DATA")]
a.datas += [('images/Gartoon_actions_mail_get_32.png','./images/Gartoon_actions_mail_get_32.png', "DATA")]
a.datas += [('images/Gartoon_actions_mail_post_to_32.png','./images/Gartoon_actions_mail_post_to_32.png', "DATA")]
a.datas += [('images/Gartoon_actions_messagebox_info_32.png','./images/Gartoon_actions_messagebox_info_32.png', "DATA")]
a.datas += [('images/Gartoon_apps_mail_32.png','./images/Gartoon_apps_mail_32.png', "DATA")]
a.datas += [('images/Gartoon_apps_package_editors_32.png','./images/Gartoon_apps_package_editors_32.png', "DATA")]
a.datas += [('images/Gartoon_filesystems_folder_tar_32.png','./images/Gartoon_filesystems_folder_tar_32.png', "DATA")]
a.datas += [('images/Gartoon_apps_mail.svg.png','./images/Gartoon_apps_mail.svg.png', "DATA")]
a.datas += [('images/OOjs_UI_icon_info_big_warning.svg.png','./images/OOjs_UI_icon_info_big_warning.svg.png', "DATA")]
a.datas += [('images/OOjs_UI_icon_eye.svg.png','./images/OOjs_UI_icon_eye.svg.png', "DATA")]
a.datas += [('images/OOjs_UI_icon_eyeClosed.svg.png','./images/OOjs_UI_icon_eyeClosed.svg.png', "DATA")]

a.datas += [('assets/about_fr.txt','./assets/about_fr.txt', "DATA")]
a.datas += [('assets/password_fr.txt','./assets/password_fr.txt', "DATA")]
a.datas += [('assets/servers.json','./assets/servers.json', "DATA")]

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='donatemail',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon=['./images/email_gui.ico'],
          version='file_version_info.txt',
         )