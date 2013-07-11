
import sys
import os
gswd=os.path.join(os.path.dirname(os.getcwd()),"GoSublime")
sys.path.append(gswd)
from gosubl import gs
from gosubl import mg9
from sublimegdb import project_path
from sublimegdb import project_pathv
from sublimegdb import pkg_pathv
from sublimegdb import GoBuilder
from sublimegdb import GDBView
from sublimegdb import get_setting
import re
import sublime
import sublime_plugin
import threading 
import subprocess
import select
import time

DOMAIN = 'GssTest'

TEST_PAT = re.compile(r'^((Test|Example|Benchmark)\w*)')
run_view=GDBView("Console", settingsprefix=None)
run_thr=None
def stop_task(win):
	aview=win.active_view()
	apath=aview.file_name()
	tlist=gs.task_list()
	gb=GoBuilder()
	gb.initEnv(False,"",win.active_view())
	if len(tlist)>0:
		for tid,t in tlist:
			if t["message"] and t["message"].find(gb.sbinp())>0:
				if t["cancel"]:
					t["cancel"]()

def runConsole(gb):
	global run_view
	global run_thr
	aview=sublime.active_window().active_view()
	sublime.active_window().set_layout(
		{
			"cols": [0.0, 1.0],
			"rows": [0.0, 0.75, 1.0],
			"cells": [[0, 0, 1, 1],[0, 1, 1, 2]]
		}
	)
	if not run_view.is_open():
		sublime.active_window().focus_group(1)
		run_view.open()
		# sublime.active_window().focus_view(aview)
	run_thr=CmdThread(gb)
	run_thr.aview=aview
	run_thr.start()

class GssSaveListener(sublime_plugin.EventListener):
	def __init__(self):
		self.loading=False
	def on_post_save(self,view):
		if self.loading and self.loading:
			return
		self.loading=True
		apath=view.file_name()
		if apath.find(".go")!=len(apath)-3:
			return
		gb=GoBuilder()
		apath=view.file_name()
		itest=apath.find("_test.go")==len(apath)-8
		gb.doGoPrj(itest,"",view)
		self.loading=False
	def on_close(self,view):
		if view.name() is None or view.name()==run_view.view.name():
			sublime.set_timeout(self.resetLayout, 1)
			run_view.view=None
			run_view.closed=True
	def resetLayout(self):
		sublime.active_window().set_layout(
                    {
                      	"cols": [0.0, 1.0],
                        "rows": [0.0, 1.0],
                        "cells": [[0, 0, 1, 1]]
                    }
            )

class GssStopCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return run_thr is not None
	def run(self):
		global run_thr
		if run_thr is not None:
			run_thr.stop()
class CmdThread(threading.Thread):
	def __init__(self,gb):
		threading.Thread.__init__(self)
		self.gb=gb
	def run(self):
		run_view.clear()
		self.proc = subprocess.Popen(["sh -c "+self.gb.binp+" "+self.gb.args],cwd=self.gb.ppath,
                       shell=True,
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                       )
		while True:
			output = self.proc.stdout.readline()
			if len(output)>0:
				run_view.add_line(output)

			if self.proc.poll() is not None:
				break
		global run_thr
		run_thr=None
		sublime.set_timeout(self.focusAview, 1)
	def stop(self):
		self.proc.kill()
		run_view.add_line("process killed")
	def focusAview(self):
		sublime.active_window().focus_view(self.aview)

class GssRunCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		aview=self.window.active_view()
		apath=aview.file_name()
		return apath is not None and  apath.find(".go")==len(apath)-3
	def run(self,debug=False):
		global run_thr
		if (run_thr is not None):
			return
		aview=self.window.active_view()
		apath=aview.file_name()
		if apath.find("_test.go")==len(apath)-8:
			self.window.run_command("gss_test")
			return
		tlist=gs.task_list()
		gb=GoBuilder()
		if not gb.doGoPrj(False,"",self.window.active_view()):
			print "build error"
			return
		if len(tlist)>0:
			for tid,t in tlist:
				if t["message"] and t["message"].find(gb.sbinp())>0:
					if t["cancel"]:
						t["cancel"]()
		runConsole(gb)
		# aview.run_command('gs9o_open', {'run': ['sh',gb.sbinp(),gb.args],'wd': project_path(self.window)})
		
class GssTestCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.window.active_view())
	def run(self,debug=False):
		global run_thr
		if (run_thr is not None):
			return
		def f(res, err):
			if err:
				gs.notify(DOMAIN, err)
				return
			mats = {}
			args = {}
			decls = res.get('file_decls', [])
			decls.extend(res.get('pkg_decls', []))
			for d in decls:
				name = d['name']
				prefix, _ =  match_prefix_name(name)
				if prefix and d['kind'] == 'func' and d['repr'] == '':
					mats[True] = prefix
					args[name] = name

			names = sorted(args.keys())
			ents = ['Run all tests and examples']
			for k in ['Test', 'Benchmark', 'Example']:
				if mats.get(k):
					s = 'Run %ss Only' % k
					ents.append(s)
					if k == 'Benchmark':
						args[s] = ['-test.run=none', '-test.bench="%s.*"' % k]
					else:
						args[s] = ['-test.run="%s.*"' % k]

			for k in names:
				ents.append(k)
				if k.startswith('Benchmark'):
					args[k] = ['-test.run=none', '-test.bench="^%s$"' % k]
				else:
					args[k] = ['-test.run="^%s$"' % k]

			def cb(i, win):
				if i >= 0:
					a = args.get(ents[i], [])
					sargs=""
					if len(a)>0:
						sargs=a[0]
					# print sargs
					if debug:
						win.run_command('gdb_launch', {'test':True,'trun':sargs})
					else:
						gb=GoBuilder()
						if not gb.doGoPrj(True,sargs,self.window.active_view()):
							print "build error"
						else:
							runConsole(gb)

			gs.show_quick_panel(ents, cb)

		win, view = gs.win_view(None, self.window)
		if view is None:
			return

		vfn = gs.view_fn(view)
		src = gs.view_src(view)
		pkg_dir = ''
		if view.file_name():
			pkg_dir = os.path.dirname(view.file_name())

		mg9.declarations(vfn, src, pkg_dir, f)


def match_prefix_name(s):
	m = TEST_PAT.match(s)
	return (m.group(2), m.group(1)) if m else ('', '')

def handle_action(view, action):
	fn = view.file_name()
	prefix, name = match_prefix_name(view.substr(view.word(gs.sel(view))))
	ok = prefix and fn and fn.endswith('_test.go')
	if ok:
		if action == 'right-click':
			pat = '^%s.*' % prefix
		else:
			pat = '^%s$' % name

		if prefix == 'Benchmark':
			cmd = ['go', 'test', '-test.run=none', '-test.bench="%s"' % pat]
		else:
			cmd = ['go', 'test', '-test.run="%s"' % pat]

		view.run_command('gs9o_open', {'run': cmd})

	return ok
