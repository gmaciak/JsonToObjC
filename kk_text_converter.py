import sublime, sublime_plugin, string, re, sys, os

sys.path.append(os.path.dirname(__file__))
from kk_base_plugin_command import *

class TextConverterCommand(BasePluginCommand):
	@staticmethod
	def reduce_mulitple_word_separators(text, sep=' '):
		while "  " in text:
			text = text.replace(sep*2, sep)
			print("reduced multiple '{}': '{}'".format(sep,text))
		return text

	@staticmethod
	def change_word_separator(sep, newSep):
		return s.replace(sep, newSep)

	@staticmethod
	def normalize_string(s, sep=' '):
		print("normalize_string {}".format(s))
		if '\t' in s:
			s = s.replace('\t', sep)
			print("replaced '\\t' '{}'".format(s))
		if '_' in s:
			s = s.replace('_', sep)
			print("replaced '_' '{}'".format(s))
		return TextConverterCommand.reduce_mulitple_word_separators(s,sep)

	@staticmethod
	def to_camel_case(s):
		if s and len(s) > 0:
			s = TextConverterCommand.normalize_string(s)
			result = s[0].lower()
			if len(s) > 1:
				if " " in s:
					result += string.capwords(s, sep=' ').replace(' ', '')[1:]
				else:
					result += s[1:]
			return result
		return s

	@staticmethod
	def to_snake_case(s):
		print("to_snake_case {}".format(s))
		return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()

	@staticmethod
	def to_pascal_case(s):
		if s and len(s) > 0:
			result = s[0].upper()
			if len(s) > 1: result += TextConverterCommand.to_camel_case(s)[1:]
			return result
		return s

class SnakeCaseCommand(TextConverterCommand):
	def run(self, edit):
		self.preform_on_selection(edit, TextConverterCommand.to_snake_case)

class CamelCaseCommand(TextConverterCommand):
	def run(self, edit):
		self.preform_on_selection(edit, TextConverterCommand.to_camel_case)

class PascalCaseCommand(TextConverterCommand):
	def run(self, edit):
		self.preform_on_selection(edit, TextConverterCommand.to_pascal_case)
