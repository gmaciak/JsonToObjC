import sublime, sublime_plugin, string, re, sys, os

sys.path.append(os.path.dirname(__file__))
from kk_plugin_command_base_v1_1 import *

class TextConverterCommand(BasePluginCommand):
	@staticmethod
	def reduce_mulitple_word_separators(s, sep=' '):
		while "  " in s:
			s = s.replace(sep*2, sep)
		return s

	@staticmethod
	def reduce_multiple_white_spaces(s, characters={' ', '\t'}):
		baseChar = characters[0] if len(characters)>0 else ' '
		for char in characters:
			s = s.replace(char, baseChar)
		s = TextConverterCommand.reduce_mulitple_word_separators(s, baseChar)
		return s

	@staticmethod
	def change_word_separator(s, separator, new_separator):
		return s.replace(separator, new_separator)

	@staticmethod
	def swap_word_separators(s, first_separator=' ', second_separator='_'):
		if first_separator in s:
			return s.replace(first_separator, second_separator)
		else:
			return s.replace(second_separator, first_separator)

	@staticmethod
	def normalize_string(s, sep=' '):
		s = s.strip()
		for ch in ['_','\t','<','=','>','-','+','(',')','!','@','#','$','%','^',
		'&','*','|','\\','/','?',',','.','\'','"',':',';','{','}','[',']','`','~']:
			if ch in s:
				s = s.replace(ch, sep)
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
		s = TextConverterCommand.normalize_string(s)
		return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower().replace(' ', "_")

	@staticmethod
	def to_pascal_case(s):
		s = TextConverterCommand.normalize_string(s)
		print(s)
		if s and len(s) > 0:
			print(string.capwords(s, sep=' ').replace(' ', ''))
			return string.capwords(s, sep=' ').replace(' ', '')
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

class ReduceMultipleWhiteSpacesCommand(TextConverterCommand):
	def run(self, edit, **args):
		self.preform_on_selection_with_args(edit, TextConverterCommand.reduce_multiple_white_spaces,args)

class SwapSpacesWithUnderscoresCommand(TextConverterCommand):
	def run(self, edit, **args):
		self.preform_on_selection_with_args(edit, TextConverterCommand.swap_word_separators, args)
