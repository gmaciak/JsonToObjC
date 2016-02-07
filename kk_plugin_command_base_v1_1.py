import sublime, sublime_plugin, sys

class BasePluginCommand(sublime_plugin.TextCommand):
	""" Case converstion command base class """
	def change_syntax(self, view = None, lang = None):
		""" Changes syntax to JSON if it is plain text """
		if view is None:
			view = self.view
		if "Plain text" in view.settings().get('syntax'):
			if lang is not None:
				if lang == "json":
					view.set_syntax_file("Packages/JavaScript/JSON.tmLanguage")
				elif lang == "objc":
					view.set_syntax_file("Packages/Objective-C/Objective-C.tmLanguage")

	def preform_on_selection(self, edit, mehtod):
		selection = self.view.sel()
		for region in selection:
			region_text = self.view.substr(region)
			converted_text = mehtod(region_text)
			self.view.replace(edit, region, converted_text)

	def preform_on_selection_with_args(self, edit, mehtod, args):
		selection = self.view.sel()
		for region in selection:
			region_text = self.view.substr(region)
			converted_text = mehtod(region_text, **args if args else None)
			self.view.replace(edit, region, converted_text)

	def show_exception(self):
		exc = sys.exc_info()[1]
		sublime.status_message(str(exc))

class CaseInsensitiveDict(dict):
	@staticmethod
	def vlaue_for_case_insensitive_key(dictionary, key):
		if key in dictionary:
			return dictionary[key]
		elif type(key) is str:
			if key.lower() in dictionary:
				return dictionary[key.lower()]
			elif key.upper() in dictionary:
				return dictionary[key.upper()]
		return None

	def __missing__(self, key):
		return CaseInsensitiveDict.vlaue_for_case_insensitive_key(self,key)