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

	def addModelNamesToJson(self, json, className = None):
		if className:
			className = settings.to_pascal_case(className)
		if type(json) is dict:
			for key in json:
				self.addModelNamesToJson(json[key], key)
			if settings.SOURCE_KEY_MODEL_CLASS_NAME not in json:
				json[settings.SOURCE_KEY_MODEL_CLASS_NAME] = className if className else self.conversionSettings.unknownClassName
			if settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME not in json:
				json[settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME] = self.conversionSettings.defaultRootClass

	def compressListToOneObject(self, listObj):
		modelDict = dict()
		for value in listObj:
			if type(value) is dict:
				modelDict.update(value)
		return modelDict if len(modelDict) else None

	def compressJson(self, json):
		if type(json) is dict:
			for key in json:
				value = json[key]
				if type(value) is list:
					pass
				self.compressJson(json[key])
		elif type(json) is list:
			result =self.compressListToOneObject(json) 
			result = self.templateJson(result)
		return result if result and len(result) else None

	def validateValuesAndKeys(self, json):
		if type(json) is dict:
			keysToRemove = list()
			if "" in json: del json[""]

	def run(self, edit):
		# settings dictionary
		settingsJSON = self.view.settings().get(settings.KEY_SETTINGS_CONVERSION_SETTINGS)
		self.conversionSettings = settings.ConversionSettings(settingsJSON)

		# remove templateS from conversion template
		if not self.view.settings().get("add_output_templates_to_new_conversion_template"):
			for key in list(settingsJSON.keys()):
				print("key: {}".format(key))
				if key.startswith("template"):
					del settingsJSON[key]
					print("deleted key: {}".format(key))
		model_json = "null // past your json instead of \"null\" value"

		allContentRegion = sublime.Region(0, self.view.size())
		if not allContentRegion.empty():
			# Get file content
			text = self.view.substr(allContentRegion).strip()

			if text.startswith("{") or text.startswith("["):
				jsonObj = sublime.decode_value(text)
				if jsonObj:
					if settings.KEY_TEMPLATE_CONVERSION_SETTINGS in jsonObj:
						if settings.KEY_TEMPLATE_MODEL_JSON in jsonObj:
							jsonObj = jsonObj[settings.KEY_TEMPLATE_MODEL_JSON]
						else:
							message = str("'Invalid json !!!"
							"\n\tJSON contains {} key but {} key is missing."
							"\n\tPlease try to generate template again using source json'").format(settings.KEY_TEMPLATE_CONVERSION_SETTINGS,settings.KEY_TEMPLATE_MODEL_JSON)
							raise ValueError(message)
					self.validateValuesAndKeys(jsonObj)
					jsonObj = self.templateJson(jsonObj)
					self.addModelNamesToJson(jsonObj, self.conversionSettings.defaultRootModelClass)
					model_json = pretty_printed(jsonObj)

		# new view
		newFileView = self.view.window().new_file()
		newFileView.set_name("JSON_TO_OBJC_CONVERSION_TEMPLATE.json")

		# template text
		templateString = """{
	"${settings_token}" : ${settings},
	// add key "${class_name_token}" to each json dictionary to define model class name
	// add key "${base_class_name_token}" to each json dictionary to define model base
	// class name (default model base class is NSObject)
	"${model_json_token}" : ${json}
}"""
		tokensMap = settings.TokensMap()
		tokensMap.settingsToken = settings.KEY_TEMPLATE_CONVERSION_SETTINGS
		tokensMap.settings = pretty_printed(settingsJSON).rstrip().replace("\n","\n\t")
		tokensMap.classNameToken = settings.SOURCE_KEY_MODEL_CLASS_NAME
		tokensMap.baseClassNameToken = settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME
		tokensMap.modelJsonToken = settings.KEY_TEMPLATE_MODEL_JSON
		tokensMap.json = model_json.replace("\n","\n\t")
		templateContent = string.Template(templateString).substitute(tokensMap)

		newFileView.insert(edit, 0, templateContent)

class JsonToObjcCommand(sublime_plugin.TextCommand):

	def propertyDescriptorsForJSON(self, json):
		descriptors = list()
		if type(json) is list and len(json) > 0:
			for obj in json:
				print("array subitem: {}",obj)
				item_descriptors = self.propertyDescriptorsForJSON(obj)
				for item in item_descriptors:
					key = item.jsonKey
					keys = [obj.jsonKey for obj in descriptors]
					if key not in keys:
						print("array item added to descriptors: ",key,item)
						descriptors.append(item)
		elif type(json) is dict and len(json) > 0:
			for key in json:
				if key == "": continue
				value = json[key]
				descriptors.append(settings.PropertyDescriptor(key, value, self.conversionSettings))
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
			defaultMap.copyright = string.Template(self.conversionSettings.templateCopyrightComment).safe_substitute(defaultMap)
		else:
			defaultMap.copyright = ""
		return defaultMap

	def interfaceCode(self, descriptors, className, baseClassName = None):
		propertiesDeclaration 	= str()
		tokensMap = settings.TokensMap()
		for descriptor in descriptors:
			tokensMap.referenceType = descriptor.referenceType
			tokensMap.type = descriptor.type
			tokensMap.name = descriptor.name
			propertiesDeclaration += string.Template(self.conversionSettings.templatePropertyDeclaration).safe_substitute(tokensMap)
		if propertiesDeclaration == "":
			propertiesDeclaration = "// No properties"

		# replacements
		replacements = self.defaultTokensMap(className)
		if baseClassName:
			replacements.baseClassName = baseClassName
		replacements.propertiesDeclaration = propertiesDeclaration
		#print("Interface replacements: {}".format(replacements))
		return string.Template(self.conversionSettings.templateHFile).safe_substitute(replacements)

	def implementationCode(self, descriptors, className, isSubclassOfKnownModel = True):
		syntesizeSection = str()
		initSection = str()
		deallocSection = str()
		initTokensMap = settings.TokensMap()
		initTokensMap.jsonDictionaryName = self.conversionSettings.initArgumentName
		templateInit = ""
		for descriptor in descriptors:
			initTokensMap.name = descriptor.name
			initTokensMap.jsonKey = descriptor.jsonKey
			if self.conversionSettings.addSynthesizeClause:
				initTokensMap.ivar = descriptor.name
			else:
				initTokensMap.ivar = "_{}".format(descriptor.name)
			if self.conversionSettings.addSynthesizeClause:
				syntesizeSection += string.Template(self.conversionSettings.templateSynthesize).safe_substitute(initTokensMap)
			
			initTokensMap.valueGetterName = descriptor.valueGetterName
			if (((descriptor.valueType is int or descriptor.valueType is float) and not self.conversionSettings.numberAsObject) or
				(descriptor.valueType is bool and not self.conversionSettings.booleanAsObject)):
				if self.conversionSettings.arcEnabled:
					templateInit = self.conversionSettings.templateArcNonObjectPropertyInitialization
				else:
					templateInit = self.conversionSettings.templateNonObjectPropertyInitialization
			else:
				if self.conversionSettings.arcEnabled:
					if descriptor.referenceType == self.conversionSettings.copyRefName:
						templateInit = self.conversionSettings.templateArcCopyPropertyInitialization
					else:
						templateInit = self.conversionSettings.templateArcStrongPropertyInitialization
				else:
					templateInit = self.conversionSettings.templatePropertyInitialization
				deallocSection += string.Template(self.conversionSettings.templateDeallocReferenceRemoving).safe_substitute(initTokensMap)
			initSection += string.Template(templateInit).safe_substitute(initTokensMap)

		replacements = self.defaultTokensMap(className)
		if self.conversionSettings.addSynthesizeClause:
			replacements.synthesizes = "{}\n\n".format(syntesizeSection)
		else:
			replacements.synthesizes = ""
		replacements.jsonDictionaryName = self.conversionSettings.initArgumentName
		replacements.initContent = initSection
		replacements.deallocCode = deallocSection

		# file template
		templateFile = string.Template(self.conversionSettings.templateMFile)
		
		# super method code
		tokensMap = settings.TransparentTokensMap()
		if isSubclassOfKnownModel:
			tokensMap.superInitMethod = self.conversionSettings.templateInheritedSuperInitMethod
		else:
			tokensMap.superInitMethod = self.conversionSettings.templateDefaultSuperInitMethod
		
		# dealloc method code
		if self.conversionSettings.arcEnabled:
			tokensMap.dealloc = ""
		else:
			tokensMap.dealloc = "{}\n\n".format(self.conversionSettings.templateDeallocMethod)

		print("Implementation tokensMap: {}".format(tokensMap))

		# insert method codes
		templateFile = templateFile.safe_substitute(tokensMap)
		print(templateFile)
		templateFile = string.Template(templateFile)
		print("Implementation replacements: {}".format(replacements))
		return templateFile.safe_substitute(replacements)

	def popDescriptorPropertyValue(self, descriptors, propertyName):
		result = None
		for descriptor in descriptors:
			if descriptor.jsonKey == propertyName:
				result = descriptor.value
				descriptors.remove(descriptor)
				break
		return result;

	def generateFiles(self, edit, jsonKey, jsonObj):
		# json descriptors
		descriptors = self.propertyDescriptorsForJSON(jsonObj)
		if len(descriptors) > 0:
			print("descriptors: {}".format(descriptors))

			className = self.popDescriptorPropertyValue(
				descriptors,
				settings.SOURCE_KEY_MODEL_CLASS_NAME)
			print("className: ", className)
			if (className is None
				and self.conversionSettings.allowPropertyKeyAsClassName
				and jsonKey is not None):
				className = settings.to_pascal_case(jsonKey)

			baseClassName = self.popDescriptorPropertyValue(
				descriptors,
				settings.SOURCE_KEY_MODEL_BASE_CLASS_NAME)

			isSubclassOfKnownModel = False
			if not baseClassName:
				baseClassName = self.conversionSettings.defaultRootClass
			elif baseClassName in self.knownModels:
				isSubclassOfKnownModel = True

			# Interface
			code = self.interfaceCode(descriptors, className, baseClassName)
			
			newFileView = self.view.window().new_file()
			newFileView.insert(edit, 0, code)

			if className and className != self.conversionSettings.unknownClassName:
				newFileView.set_name("{}.h".format(className))
				self.knownModels.append(className)

			# Implementation
			code = self.implementationCode(descriptors, className, isSubclassOfKnownModel)

			newFileView = self.view.window().new_file()
			newFileView.insert(edit, 0, code)

			if className and className != self.conversionSettings.unknownClassName:
				newFileView.set_name("{}.m".format(className))

			for descriptor in descriptors:
				if "value" in descriptor:
					value = descriptor.value
					if type(value) is dict or type(value) is list:
						self.generateFiles(edit, descriptor.jsonKey, value)

	def run(self, edit):
		self.knownModels = list()

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
				if settings.KEY_TEMPLATE_CONVERSION_SETTINGS in jsonObj:
					explicit_settings = jsonObj[settings.KEY_TEMPLATE_CONVERSION_SETTINGS]
					if explicit_settings:
						settingsJSON.update(explicit_settings)
					jsonObj = jsonObj[settings.KEY_TEMPLATE_MODEL_JSON]

			# plugin settings object
			self.conversionSettings = settings.ConversionSettings(settingsJSON)

			self.generateFiles(edit, self.conversionSettings.defaultRootModelClass, jsonObj)
