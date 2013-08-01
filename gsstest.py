
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
from sublimegdb import CmdThread
from sublimegdb import n_console_view
import re
import sublime
import sublime_plugin
import threading 
import subprocess
import select
import time

DOMAIN = 'GssTest'

TEST_PAT = re.compile(r'^((Test|Example|Benchmark)\w*)')
w_builders={}
class GssShowConsole(sublime_plugin.WindowCommand):
	def is_enabled(self):
		print n_console_view.listener(self.window)
		return n_console_view.listener(self.window)==None
	def run(self):
		sublime.active_window().set_layout(
			{
			"cols": [0.0, 1.0],
			"rows": [0.0, 0.75, 1.0],
			"cells": [[0, 0, 1, 1],[0, 1, 1, 2]]
			})
		n_console_view.ShowConsoleView(self.window)
class GssShowDebug(sublime_plugin.WindowCommand):
	def run(self):
		print n_console_view.logs
		print n_console_view.listeners
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
		apath=view.file_name()
		itest=apath.find("_test.go")==len(apath)-8
		global g_builder
		g_builder=GoBuilder()
		g_builder.initEnv(itest,"",view,n_console_view)
		# g_builder.showLView()
		g_builder.build(False)
		self.loading=False
	def on_close(self,view):
		if view.name()=="Console":
			n_console_view.rm_listener(sublime.active_window())
			sublime.set_timeout(self.resetLayout, 1)
			# n_console_view.view=None
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
		global w_builders
		g_builder=None
		wid=self.window.id()
		if w_builders.has_key(wid):
			g_builder=w_builders[wid]
		return g_builder is not None and g_builder.is_running()
	def run(self):
		global w_builders
		g_builder=None
		wid=self.window.id()
		if w_builders.has_key(wid):
			g_builder=w_builders[wid]
		if g_builder is not None:
			g_builder.bstop()
			g_builder.rstop()
class GssRunCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		aview=self.window.active_view()
		apath=aview.file_name()
		return apath is not None and  apath.find(".go")==len(apath)-3
	def run(self,debug=False):
		global w_builders
		g_builder=None
		wid=self.window.id()
		if w_builders.has_key(wid):
			g_builder=w_builders[wid]
		if (g_builder is not None) and (g_builder.is_running()):
			return
		aview=self.window.active_view()
		apath=aview.file_name()
		if apath.find("_test.go")==len(apath)-8:
			self.window.run_command("gss_test")
			return
		g_builder=GoBuilder()
		g_builder.initEnv(False,"",self.window.active_view(),n_console_view)
		w_builders[wid]=g_builder
		g_builder.run()
		# aview.run_command('gs9o_open', {'run': ['sh',gb.sbinp(),gb.args],'wd': project_path(self.window)})
		
class GssTestCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.window.active_view())
	def run(self,debug=False):
		global w_builders
		g_builder=None
		wid=self.window.id()
		if w_builders.has_key(wid):
			g_builder=w_builders[wid]
		if (g_builder is not None) and (g_builder.is_running()):
			g_builder.showLView()
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
						global g_builder
						g_builder=GoBuilder()
						g_builder.initEnv(True,sargs,self.window.active_view(),n_console_view)
						g_builder.run()

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
