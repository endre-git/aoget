pyinstaller aoget_test.spec
xcopy /E ..\config.json dist
md dist\aoget\aoget
xcopy qt dist\aoget\aoget\qt /E /I /H
xcopy resources dist\aoget\aoget\resources /E /I /H
xcopy ..\config.json dist\aoget
md dist\aoget\settings

