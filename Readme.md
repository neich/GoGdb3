GoGdb Sublime Text 2 Plugin.
===

###Description
Golang GDB plugin for Sublime Text 2,it modify base of <https://github.com/quarnster/SublimeGDB>.
if you have some question,send message to <https://github.com/Centny/GoGdb/issues>


First,thanks quarnster's code of Gdb plugin.

###Installation
- The easiest way to install GoGdb is via the excellent Package Control Plugin
	- See http://wbond.net/sublime_packages/package_control/installation
	- Once package control has been installed, bring up the command palette (cmd+shift+P or ctrl+shift+P)
	- Type Install and select "Package Control: Install Package"
	- Select GoGdb from the list. Package Control will keep it automatically updated for you
- If you don't want to use package control, you can manually install it
	- Go to your packages directory and type:see below manual install.
	
	```
	OSX:
	cd ~/Library/Application\ Support/Sublime\ Text\ 2/Packages/
	git clone https://github.com/Centny/GoGdb
	
	
	Linux:
	cd ~/.config/sublime-text-2/Packages
	git clone https://github.com/Centny/GoGdb
	```
- Back in the editor, open up the command palette by pressing cmd+shift+P or ctrl+shift+P
- Type GoGdb and open up the settings file you want to modify

###Windows Configure
download the gdb.
###Usage

most of the features is sampe of <https://github.com/quarnster/SublimeGDB>,you can see it and configure by yourself.

new features:
* debug the golang project.
* debug the golang unit test.
* build log view.
* run command

for new features detail,see this article:<a href="https://github.com/Centny/Centny/blob/master/Articles/How%20to%20configure%20golang%20develop%20environment%20with%20debug%20and%20unit%20test%20debug.md">How to configure golang develop environment with debug and unit test debug</a>

