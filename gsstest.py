from gosubl import gs
from gosubl import mg9
from sublimegdb import project_path
from sublimegdb import GoBuilder
import os
import re
import sublime
import sublime_plugin

DOMAIN = 'GssTest'

TEST_PAT = re.compile(r'^((Test|Example|Benchmark)\w*)')

def stop_task(win):
	aview=win.active_view()
	apath=aview.file_name()
	tlist=gs.task_list()
	gb=GoBuilder()
	gb.initEnv(False,"",win,win.active_view())
	if len(tlist)>0:
		for tid,t in tlist:
			if t["message"] and t["message"].find(gb.sbinp())>0:
				if t["cancel"]:
					t["cancel"]()

class GssStopCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return True
	def run(self):
		stop_task(self.window)

class GssRunCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return True
	def run(self,debug=False):
		aview=self.window.active_view()
		apath=aview.file_name()
		if apath.find("_test.go")==len(apath)-8:
			self.window.run_command("gss_test")
			return
		tlist=gs.task_list()
		gb=GoBuilder()
		if not gb.doGoPrj(False,"",self.window,self.window.active_view()):
			print "build error"
			return
		if len(tlist)>0:
			for tid,t in tlist:
				if t["message"] and t["message"].find(gb.sbinp())>0:
					if t["cancel"]:
						t["cancel"]()
		aview.run_command('gs9o_open', {'run': ['sh',gb.sbinp(),gb.args],'wd': project_path(self.window)})
		
class GssTestCommand(sublime_plugin.WindowCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.window.active_view())
	def run(self,debug=False):
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
						if not gb.doGoPrj(True,sargs,self.window,self.window.active_view()):
							print "build err"
						else:
							win.run_command('gs9o_open', {'run': ['sh',gb.sbinp(),sargs],'wd':gb.ppath })

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
