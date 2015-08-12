import sublime
import sublime_plugin
import json
import datetime
import os, sys, string

#sys.path.append(os.path.join(os.path.dirname(__file__), "modules"))
sys.path.append(os.path.dirname(__file__))
import settings

def pretty_printed(value):
	return sublime.encode_value(value, True)

class NewJsonToObjcWindowCommand(sublime_plugin.TextCommand):
	def addModelNamesToJson(self, json):
		if type(json) is dict:
			for key in json:
				self.addModelNamesToJson(json[key])
			if settings.SOURCE_KEY_MODEL_CLASS_NAME not in json:
				json[settings.SOURCE_KEY_MODEL_CLASS_NAME] = "<#class_name#>"
			if settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME not in json:
				json[settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME] = self.conversionSettings.defaultRootClass
		elif type(json) is list:
			for value in json:
				self.addModelNamesToJson(value)

	def run(self, edit):
		# settings dictionary
		settingsJSON = self.view.settings().get(settings.KEY_SETTINGS_CONVERSION_SETTINGS)
		self.conversionSettings = settings.ConversionSettings(settingsJSON)

		if not self.view.settings().get("add_output_templates_to_new_conversion_template", True):
			for key in list(settingsJSON.keys()):
				print("key: {}".format(key))
				if key.endswith("template"):
					del settingsJSON[key]
					print("deleted key: {}".format(key))
		json = "null // past your json instead of \"null\" value"

		allContentRegion = sublime.Region(0, self.view.size())
		if not allContentRegion.empty():
			# Get file content
			text = self.view.substr(allContentRegion)

			jsonObj = sublime.decode_value(text)
			if jsonObj:
				if settings.KEY_SETTINGS_CONVERSION_SETTINGS not in jsonObj:
					json = pretty_printed(jsonObj)
				elif "json" in jsonObj:
					jsonObj = jsonObj["json"]
					
			self.addModelNamesToJson(jsonObj)
			json = pretty_printed(jsonObj)

		# new view
		newFileView = self.view.window().new_file()
		newFileView.set_name("JSON_TO_OBJC_CONVERSION_TEMPLATE.json")

		# template text
		templateString = """{
	"${settings_key}" : ${settings},
	// add key "__CLASS_NAME__" to each json dictionary to define model class name
	// add key "__BASE_CLASS_NAME__" to each json dictionary to define model base
	// class name (default model base class is NSObject)
	"json" : ${json}
}"""
		tokensMap = settings.TokensMap()
		tokensMap.settingsKey = settings.KEY_SETTINGS_CONVERSION_SETTINGS
		tokensMap.settings = pretty_printed(settingsJSON).rstrip().replace("\n","\n\t")
		tokensMap.json = json.replace("\n","\n\t")
		templateContent = string.Template(templateString).substitute(tokensMap)

		newFileView.insert(edit, 0, templateContent)

class JsonToObjcCommand(sublime_plugin.TextCommand):

	def propertyDescriptorsForJSON(self, json):
		descriptors = dict()
		if type(json) is list and len(json) > 0:
			temp_descirptors = dict()
			for value in json:
				item_descriptors = self.propertyDescriptorsForJSON(value)
				for key in item_descriptors:
					if key not in temp_descirptors: temp_descirptors[key] = item_descriptors[key]
		elif type(json) is dict and len(json) > 0:
			for key in json:
				if key == "": continue
				value = json[key]
				descriptors[key] = settings.PropertyDescriptor(key, value, self.conversionSettings)
		return descriptors 

	def defaultTokensMap(self, className):
		defaultMap = settings.TokensMap()
		defaultMap.date          = datetime.datetime.now().strftime("%d.%m.%Y")
		defaultMap.year          = datetime.datetime.now().strftime("%Y")
		defaultMap.baseClassName = self.conversionSettings.defaultRootClass
		defaultMap.className     = className or self.conversionSettings.unknownClassName
		if self.conversionSettings.projectName:
			defaultMap.projectName = self.conversionSettings.projectName
		if self.conversionSettings.creator:
			defaultMap.creator = self.conversionSettings.creator
		if self.conversionSettings.organization:
			defaultMap.organization = self.conversionSettings.organization
		if self.conversionSettings.addStandardCopyrightComment:
			defaultMap.copyright = string.Template(self.conversionSettings.copyrightCommentTemplate).safe_substitute(defaultMap)
		else:
			defaultMap.copyright = ""
		return defaultMap

	def interfaceCode(self, descriptors, className):
		propertiesDeclaration 	= str()
		tokensMap = settings.TokensMap()
		for key in descriptors:
			descriptor = descriptors[key]
			tokensMap.referenceType = descriptor.referenceType
			tokensMap.type = descriptor.type
			tokensMap.name = key
			propertiesDeclaration += string.Template(self.conversionSettings.propertyDeclarationTemplate).safe_substitute(tokensMap)
		if propertiesDeclaration == "": propertiesDeclaration = "// No properties"
		replacements = self.defaultTokensMap(className)
		replacements.propertiesDeclaration = propertiesDeclaration
		print("Interface replacements: {}".format(replacements))
		return string.Template(self.conversionSettings.hFileTemplate).safe_substitute(replacements)

	def implementationCode(self, descriptors, className, isBaseClassDefault = True):
		syntesizeSection = str()
		initSection = str()
		deallocSection = str()
		initTokensMap = settings.TokensMap()
		initTokensMap.jsonDictionaryName = self.conversionSettings.initArgumentName
		initTemplate = ""
		for key in descriptors:
			descriptor = descriptors[key]
			initTokensMap.name = key
			if self.conversionSettings.addSynthesizeClause:
				syntesizeSection += string.Template(self.conversionSettings.synthesizeTemplate).safe_substitute(initTokensMap)
			
			initTokensMap.valueGetterName = descriptor.valueGetterName
			if (((descriptor.valueType is int or descriptor.valueType is float) and not self.conversionSettings.numberAsObject) or
				(descriptor.valueType is bool and not self.conversionSettings.booleanAsObject)):
				initTemplate = self.conversionSettings.nonObjectPropertyInitializationTemplate
			else:
				initTemplate = self.conversionSettings.propertyInitializationTemplate
				deallocSection += string.Template(self.conversionSettings.deallocReferenceRemovingTemplate).safe_substitute(initTokensMap)
			initSection += string.Template(initTemplate).safe_substitute(initTokensMap)

		replacements = self.defaultTokensMap(className)
		replacements.synthesizes = syntesizeSection
		replacements.jsonDictionaryName = self.conversionSettings.initArgumentName
		replacements.initContent = initSection
		replacements.deallocCode = deallocSection

		# file template
		fileTemplate = string.Template(self.conversionSettings.mFileTemplate)
		
		# super method code
		tokensMap = settings.TransparentTokensMap()
		if isBaseClassDefault:
			tokensMap.superInitMethod = self.conversionSettings.defaultSuperInitMethodTemplate
		else:
			tokensMap.superInitMethod = self.conversionSettings.inheritedSuperInitMethodTemplate
		
		# dealloc method code
		if self.conversionSettings.arcEnabled:
			tokensMap.dealloc = ""
		else:
			tokensMap.dealloc = self.conversionSettings.deallocMethodTemplate

		print("Implementation tokensMap: {}".format(tokensMap))

		# insert method codes
		fileTemplate = fileTemplate.safe_substitute(tokensMap)
		print(fileTemplate)
		fileTemplate = string.Template(fileTemplate)
		print("Implementation replacements: {}".format(replacements))
		return fileTemplate.safe_substitute(replacements)

	def popDescriptorPropertyValue(self, descriptors, propertyName):
		result = ""
		for key in descriptors:
			descriptor = descriptors[key]
			if key == propertyName:
				# in this case value is a string
				result = descriptor.value
				del(descriptors[key])
				break
		return result;

	def generateFiles(self, edit, jsonObj):
		# json descriptors
		descriptors = self.propertyDescriptorsForJSON(jsonObj)
		if len(descriptors) > 0:
			# print("descriptors: {}".format(pretty_printed(descriptors)))

			className = self.popDescriptorPropertyValue(
				descriptors,
				settings.SOURCE_KEY_MODEL_CLASS_NAME)

			isBaseClassDefault = True
			baseClassName = self.popDescriptorPropertyValue(
				descriptors,
				settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME)

			if baseClassName == "":
				baseClassName = self.conversionSettings.defaultRootClass
			else:
				isBaseClassDefault = False

			# Interface
			code = self.interfaceCode(descriptors, className)
			# text = "/*\n{}\n*/\n\n{}".format(text,code)
			
			newFileView = self.view.window().new_file()
			newFileView.insert(edit, 0, code)
			# newFileView.replace(edit, sublime.Region(0, self.view.size()), code)
			if className != self.conversionSettings.unknownClassName:
				newFileView.set_name("{}.h".format(className))

			# Implementation
			code = self.implementationCode(descriptors, className, isBaseClassDefault)

			newFileView = self.view.window().new_file()
			newFileView.insert(edit, 0, code)
			# newFileView.replace(edit, sublime.Region(0, self.view.size()), code)
			if className != self.conversionSettings.unknownClassName:
				newFileView.set_name("{}.m".format(className))

			# print("view.buffer_id() = {}".format(newFileView.buffer_id()))
			# print("view.file_name() = {}".format(newFileView.file_name()))
			# print("view.name() = {}".format(newFileView.name()))
			# print("view.is_loading() = {}".format(newFileView.is_loading()))
			# print("view.is_dirty() = {}".format(newFileView.is_dirty()))
			# print("view.is_read_only() = {}".format(newFileView.is_read_only()))
			# print("view.is_scratch() = {}".format(newFileView.is_scratch()))
			# print("\tview.window().id() = {}".format(newFileView.window().id()))
			# print("\tview.window().active_view() = {}".format(newFileView.window().active_view()))
			# print("\tview.window().views() = {}".format(newFileView.window().views()))

			for key in descriptors:
				descriptor = descriptors[key]
				if "value" in descriptor:
					value = descriptor.value
					if type(value) is dict or type(value) is list:
						self.generateFiles(edit, value)

	def run(self, edit):
		# self.logBasicEnviromentProperties()
		

		allContentRegion = sublime.Region(0, self.view.size())
		if not allContentRegion.empty():
			# settings
			settingsJSON = self.view.settings().get(settings.KEY_SETTINGS_CONVERSION_SETTINGS)
			
			# Get file content
			text = self.view.substr(allContentRegion)

			jsonObj = sublime.decode_value(text)
			# print("JSON: {}".format(pretty_printed(jsonObj)))

			# direct settings dictionary from processed json file
			if  type(jsonObj) is dict:
				if settings.KEY_SETTINGS_CONVERSION_SETTINGS in jsonObj:
					explicit_settings = jsonObj[settings.KEY_SETTINGS_CONVERSION_SETTINGS]
					for key in explicit_settings:
						settingsJSON[key] = explicit_settings[key]
					jsonObj = jsonObj["json"]

			# plugin settings object
			self.conversionSettings = settings.ConversionSettings(settingsJSON)

			self.generateFiles(edit, jsonObj)
