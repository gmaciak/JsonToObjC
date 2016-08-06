import sublime, sublime_plugin, string, re, sys, os

# v 1.1

# change log
# v 1.1 added permutation command

sys.path.append(os.path.dirname(__file__))
from kk_plugin_command_base_v1_1 import *

class KKTextConverterCommand(KKBasePluginCommand):
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
		s = KKTextConverterCommand.reduce_mulitple_word_separators(s, baseChar)
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
		return KKTextConverterCommand.reduce_mulitple_word_separators(s,sep)

	@staticmethod
	def to_camel_case(s):
		if s and len(s) > 0:
			s = KKTextConverterCommand.normalize_string(s)
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
		s = KKTextConverterCommand.normalize_string(s)
		return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower().replace(' ', "_")

	@staticmethod
	def to_pascal_case(s):
		s = KKTextConverterCommand.normalize_string(s)
		print(s)
		if s and len(s) > 0:
			print(string.capwords(s, sep=' ').replace(' ', ''))
			return string.capwords(s, sep=' ').replace(' ', '')
		return s

	def _heap_perm_(self, edit, n, A, output):
		# print ("step 1 n={}: {}".format(n, A))
		if n == 1:
			# print ("*{} {}".format("#"*n,A))
			output.append(list(A))
			if (len(output) > 99): self.printPartialResultAndClearOutput(edit, output)
		else:
			for i in range(n-1):
				self._heap_perm_(edit, n-1, A, output)
				j = 0 if (n % 2) == 1 else i
				A[j],A[n-1] = A[n-1],A[j]
			self._heap_perm_(edit, n-1, A, output)

	def printPartialResultAndClearOutput(self, edit, output):
		self.count += len(output)
		outputText = "{}\n".format("\n".join(["".join(sequence) for sequence in output]))
		output.clear()
		self.view.insert(edit, self.view.size(), outputText)
	

class PermutationsCommand(KKTextConverterCommand):
	def run(self, edit):
		allContentRegion = sublime.Region(0, self.view.size())
		if not allContentRegion.empty():
		# Get file content
			text = self.view.substr(allContentRegion)
			words = text.split("\n")
			if len(words) > 10:
				print("TO MANY WORDS, max 10")
				sublime.status_message("TO MANY WORDS, max 10")
			output = []
			f = lambda x: x * f(x-1) if x != 0 else 1
			self.total = f(len(words))
			self.count = 0
			print("Total: {}".format(self.total))
			self.view.replace(edit, allContentRegion, "")
			self._heap_perm_(edit, len(words), words, output)
			self.printPartialResultAndClearOutput(edit, output)
			

class SnakeCaseCommand(KKTextConverterCommand):
	def run(self, edit):
		self.preform_on_selection(edit, KKTextConverterCommand.to_snake_case)

class CamelCaseCommand(KKTextConverterCommand):
	def run(self, edit):
		self.preform_on_selection(edit, KKTextConverterCommand.to_camel_case)

class PascalCaseCommand(KKTextConverterCommand):
	def run(self, edit):
		self.preform_on_selection(edit, KKTextConverterCommand.to_pascal_case)

class ReduceMultipleWhiteSpacesCommand(KKTextConverterCommand):
	def run(self, edit, **args):
		self.preform_on_selection_with_args(edit, KKTextConverterCommand.reduce_multiple_white_spaces,args)

class SwapSpacesWithUnderscoresCommand(KKTextConverterCommand):
	def run(self, edit, **args):
		self.preform_on_selection_with_args(edit, KKTextConverterCommand.swap_word_separators, args)
