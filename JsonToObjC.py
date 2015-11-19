import sublime
import sublime_plugin
import json
import datetime
import os, sys, string, re

#sys.path.append(os.path.join(os.path.dirname(__file__), "modules"))
sys.path.append(os.path.dirname(__file__))
import json_to_objc_models_and_constants as models

class JsonToObjcSnakeCaseCommand(models.JsonToObjcConvertCaseBaseCommand):
	def run(self, edit):
		self.preform_on_selection(edit, models.Default.to_snake_case)

class JsonToObjcCamelCaseCommand(models.JsonToObjcConvertCaseBaseCommand):
	def run(self, edit):
		self.preform_on_selection(edit, models.Default.to_camel_case)

class JsonToObjcPascalCaseCommand(models.JsonToObjcConvertCaseBaseCommand):
	def run(self, edit):
		self.preform_on_selection(edit, models.Default.to_pascal_case)

class JsonToObjcPrettyPrintCommand(models.JsonToObjcBaseCommand):
	def run(self, edit):
		selection = self.view.sel()
		for region in selection:
			region_text = self.view.substr(region)
			try:
				obj = sublime.decode_value(region_text)
				converted_text = sublime.encode_value(obj, True)
				self.view.replace(edit, region, converted_text)
			except ValueError:
				self.show_exception()

class JsonToObjcNewTemplateCommand(models.JsonToObjcBaseCommand):

	def add_model_names_to_json(self, json, className = None):
		if className:
			className = models.ConversionSettings.to_pascal_case(className)
		if type(json) is dict:
			for key in json:
				self.add_model_names_to_json(json[key], key)
			if models.SOURCE_KEY_MODEL_CLASS_NAME not in json:
				if className:
					json[models.SOURCE_KEY_MODEL_CLASS_NAME] = className
				else:
					json[models.SOURCE_KEY_MODEL_CLASS_NAME] = self.conversionSettings.unknownClassName
			if models.SOURCE_KEY_MODEL_BASE_CLASS_NAME not in json:
				json[models.SOURCE_KEY_MODEL_BASE_CLASS_NAME] = self.conversionSettings.defaultRootClass

	def compress_list_to_one_object(self, listObj):
		modelDict = dict()
		for value in listObj:
			if type(value) is dict:
				modelDict.update(value)
		return modelDict if len(modelDict) else None

	def compress_json(self, json):
		if type(json) is dict:
			for key in json:
				value = json[key]
				if type(value) is list:
					pass
				self.compress_json(json[key])
		elif type(json) is list:
			result = self.compress_list_to_one_object(json) 
			result = self.templateJson(result)
		return result if result and len(result) else None

	def validate_values_and_keys(self, json):
		if type(json) is dict:
			if "" in json: del json[""]

	def run(self, edit, **args):

		# settings dictionary
		settingsJSON = self.view.settings().get(models.KEY_SETTINGS_CONVERSION_SETTINGS, dict())
		self.conversionSettings = models.ConversionSettings(settingsJSON)

		# remove templateS from conversion template
		key = "add_output_templates_to_new_conversion_template"
		shouldIncludeTemplates = False
		if key in args and type(args[key]) is bool:
			shouldIncludeTemplates = args[key]
		else:
			shouldIncludeTemplates = self.view.settings().get(key, False)
		if not shouldIncludeTemplates:
			for key in list(settingsJSON.keys()):
				if key.startswith("template"):
					del settingsJSON[key]
		if "class_name_prefix" not in settingsJSON:
			settingsJSON["class_name_prefix"] = self.conversionSettings.classNamePrefix

		# default json of model definition node value
		model_json = "null // past your json instead of \"null\" value"

		# Get file content
		text = self.view.substr(sublime.Region(0, self.view.size())).strip()
		if len(text) > 0:
			try:
				if text.startswith("{") or text.startswith("["):
					jsonObj = sublime.decode_value(text)
					if jsonObj:
						if models.KEY_TEMPLATE_CONVERSION_SETTINGS in jsonObj:
							if models.KEY_TEMPLATE_MODEL_JSON in jsonObj:
								jsonObj = jsonObj[models.KEY_TEMPLATE_MODEL_JSON]
							else:
								message = str("'Invalid json !!!"
								"\n\tJSON contains {} key but {} key is missing."
								"\n\tPlease try to generate template again using source json'"
								).format(models.KEY_TEMPLATE_CONVERSION_SETTINGS,models.KEY_TEMPLATE_MODEL_JSON)
								raise ValueError(message)
						self.validate_values_and_keys(jsonObj)
						self.add_model_names_to_json(jsonObj, self.conversionSettings.defaultRootModelClass)
						model_json = models.pretty_printed(jsonObj)
				else:
					message = str("'Invalid json !!!"
					"\n\tJSON must starts with '{' or '['")
					raise ValueError(message)
			except Exception:
				self.show_exception()

		# new view
		newFileView = self.view.window().new_file()
		newFileView.set_name("JSON_TO_OBJC_CONVERSION_TEMPLATE.json")

		# set syntax
		self.change_syntax(newFileView);

		# template text
		templateString ="""{
	// Change following settings if needed
	"${settings_token}" : ${settings},

	// Replace following node value with JSON you want to convert.
	// Add key "${class_name_token}" to each json dictionary to define model class name.
	// Add key "${base_class_name_token}" to each json dictionary to define model base
	// class name (default model base class is NSObject)
	"${model_json_token}" : ${json}
}
"""
		tokensMap = models.TokensMap()
		tokensMap.settingsToken = models.KEY_TEMPLATE_CONVERSION_SETTINGS
		tokensMap.settings = models.pretty_printed(settingsJSON).rstrip().replace("\n","\n\t")
		tokensMap.classNameToken = models.SOURCE_KEY_MODEL_CLASS_NAME
		tokensMap.baseClassNameToken = models.SOURCE_KEY_MODEL_BASE_CLASS_NAME
		tokensMap.modelJsonToken = models.KEY_TEMPLATE_MODEL_JSON
		tokensMap.json = model_json.replace("\n","\n\t")
		templateContent = string.Template(templateString).substitute(tokensMap)

		newFileView.insert(edit, 0, templateContent)

class JsonToObjcCommand(models.JsonToObjcBaseCommand):

	def property_descriptors_list_for_json(self, json):
		"""  """
		descriptors = list()
		# merge all subitems properties
		if type(json) is list and len(json) > 0:
			for obj in json:
				print("array subitem: {}",obj)
				item_descriptors = self.property_descriptors_list_for_json(obj)
				for item in item_descriptors:
					key = item.jsonKey
					prevItem = next((x for x in descriptors if x.jsonKey == key), None)
					
					if prevItem is None:
						print("array item added to descriptors: ",key,item)
						descriptors.append(item)
					# if one of property values shows that it can be null update
					# previewous property definition
					else:
						# if previous item is None the definition is not full,
						# for eg. value type is not specified, so
						# we should use new item which may be more precise
						if prevItem.valueType is type(None):
							item.isNullable = True
							descriptors.remove(prevItem)
							descriptors.append(item)
						elif item.isNullable:
							prevItem.isNullable = True;
						

		elif type(json) is dict and len(json) > 0:
			for key in json:
				if key == "": continue
				value = json[key]
				descriptors.append(models.PropertyDescriptor(key, value, self.conversionSettings))
		return descriptors 

	def default_tokens_replacements_map(self, className):
		"""  """
		defaultMap = models.TokensMap()
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
		else:
			defaultMap.copyright = ""
		return defaultMap

	def interface_code(self, descriptors, className, baseClassName = None, isSubclassOfKnownModel = False):
		"""  """
		propertiesDeclaration 	= str()
		# property declaration template tokens replacements
		tokensMap = models.TokensMap()
		for descriptor in descriptors:
			if descriptor.isNullable:
				tokensMap.referenceType = "{},{}".format(descriptor.referenceType,"nullable")
			else:
				tokensMap.referenceType = descriptor.referenceType
			tokensMap.type = descriptor.type
			tokensMap.name = descriptor.name
			propertiesDeclaration += string.Template(
				self.conversionSettings.templateHProperty).safe_substitute(tokensMap)
		if propertiesDeclaration == "":
			propertiesDeclaration = "// No properties"

		# interface template tokens replacements
		tokensMap = self.default_tokens_replacements_map(className)

		# copy rights
		if self.conversionSettings.addStandardCopyrightComment:
			tokensMap.copyright = string.Template(
				self.conversionSettings.templateHCopyrightComment).safe_substitute(tokensMap)

		# base class
		if baseClassName:
			tokensMap.baseClassName = baseClassName

		# properties delcaration region
		tokensMap.propertiesDeclaration = propertiesDeclaration

		# designed initializer declaration
		if isSubclassOfKnownModel:
			tokensMap.designedInitializer = ""
		else:
			tokensMap.designedInitializer = self.conversionSettings.templateHDesignedInitializer
			
		#print("Interface tokensMap: {}".format(tokensMap))
		return string.Template(self.conversionSettings.templateHFile).safe_substitute(tokensMap)

	def implementation_code(self, descriptors, className, isSubclassOfKnownModel = False):
		"""  """
		syntesizeSection = str()
		initSection 	= str()
		deallocSection = str()
		initTokensMap = models.TokensMap()
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
				syntesizeSection += string.Template(self.conversionSettings.templateMSynthesize).safe_substitute(initTokensMap)
			
			initTokensMap.valueGetterName = descriptor.valueGetterName
			if (((descriptor.valueType is int or descriptor.valueType is float) and not self.conversionSettings.numberAsObject) or
				(descriptor.valueType is bool and not self.conversionSettings.booleanAsObject)):
				if self.conversionSettings.arcEnabled:
					templateInit = self.conversionSettings.templateMArcNonObjectPropertyInitialization
				else:
					templateInit = self.conversionSettings.templateMNonObjectPropertyInitialization
			else:
				if self.conversionSettings.arcEnabled:
					if descriptor.referenceType == self.conversionSettings.copyRefName:
						templateInit = self.conversionSettings.templateMArcCopyPropertyInitialization
					else:
						templateInit = self.conversionSettings.templateMArcStrongPropertyInitialization
				else:
					templateInit = self.conversionSettings.templateMPropertyInitialization
				deallocSection += string.Template(self.conversionSettings.templateMDeallocReferenceRemoving).safe_substitute(initTokensMap)
			initSection += string.Template(templateInit).safe_substitute(initTokensMap)

		# interface template tokens replacements
		tokensMap = self.default_tokens_replacements_map(className)

		# copy rights
		if self.conversionSettings.addStandardCopyrightComment:
			tokensMap.copyright = string.Template(
				self.conversionSettings.templateMCopyrightComment).safe_substitute(tokensMap)

		# sythesizes region
		if self.conversionSettings.addSynthesizeClause:
			tokensMap.synthesizes = "{}\n".format(syntesizeSection)
		else:
			tokensMap.synthesizes = ""

		tokensMap.jsonDictionaryName = self.conversionSettings.initArgumentName
		tokensMap.initContent = initSection
		tokensMap.deallocCode = deallocSection

		# file template
		templateFile = string.Template(self.conversionSettings.templateMFile)
		
		# super method code template tokens replacements
		methodsTokensMap = models.TransparentTokensMap()
		if isSubclassOfKnownModel:
			methodsTokensMap.superInitMethod = self.conversionSettings.templateMInheritedSuperInitMethod
		else:
			methodsTokensMap.superInitMethod = self.conversionSettings.templateMDefaultSuperInitMethod
		
		# dealloc method code
		if self.conversionSettings.arcEnabled:
			methodsTokensMap.dealloc = ""
		else:
			methodsTokensMap.dealloc = self.conversionSettings.templateMDeallocMethod
		#print("Implementation methodsTokensMap: {}".format(methodsTokensMap))

		# insert methods code (generate final templet string)
		templateFile = templateFile.safe_substitute(methodsTokensMap)

		# last step template
		templateFile = string.Template(templateFile)
		#print("Implementation tokensMap: {}".format(tokensMap))
		return templateFile.safe_substitute(tokensMap)

	def pop_descriptor_property_value(self, descriptors, propertyName):
		"""  """
		result = None
		for descriptor in descriptors:
			if descriptor.jsonKey == propertyName:
				result = descriptor.value
				descriptors.remove(descriptor)
				break
		return result;

	def prefixed_class_name(self, className):
		return "{}{}".format(self.conversionSettings.classNamePrefix, className)

	def generate_files(self, edit, jsonKey, jsonObj):
		"""  """
		# json descriptors
		descriptors = self.property_descriptors_list_for_json(jsonObj)
		if self.conversionSettings.sortPropertiesByName:
			descriptors.sort(key=lambda descriptor: descriptor.name)

		if len(descriptors) > 0:
			# ROOT MODEL FILES GENERATION

			# model class name
			className = self.pop_descriptor_property_value(
				descriptors,
				models.SOURCE_KEY_MODEL_CLASS_NAME)
			print("className: ", className)
			if (className is None):
				if (self.conversionSettings.allowPropertyKeyAsClassName
					and jsonKey is not None):
					className = models.ConversionSettings.to_pascal_case(jsonKey)
					className = self.prefixed_class_name(className)
			else:
				className = self.prefixed_class_name(className)

			# model base class name
			baseClassName = self.pop_descriptor_property_value(
				descriptors,
				models.SOURCE_KEY_MODEL_BASE_CLASS_NAME)
			isSubclassOfKnownModel = False
			if not baseClassName:
				baseClassName = self.conversionSettings.defaultRootClass
			elif self.prefixed_class_name(baseClassName) in self.knownModels:
				isSubclassOfKnownModel = True
				baseClassName = self.prefixed_class_name(baseClassName)

			# Interface code
			code = self.interface_code(descriptors, className, baseClassName, isSubclassOfKnownModel)
			
			# Interface file (.h)
			newFileView = self.view.window().new_file()
			newFileView.insert(edit, 0, code)

			if className and className != self.conversionSettings.unknownClassName:
				newFileView.set_name("{}.h".format(className))
				self.knownModels.append(className)

			# Implementation code
			code = self.implementation_code(descriptors, className, isSubclassOfKnownModel)

			# Implementation file (.h)
			newFileView = self.view.window().new_file()
			newFileView.insert(edit, 0, code)

			if className and className != self.conversionSettings.unknownClassName:
				newFileView.set_name("{}.m".format(className))

			# recursively other mothels in the tree
			for descriptor in descriptors:
				if "value" in descriptor:
					value = descriptor.value
					if type(value) is dict or type(value) is list:
						self.generate_files(edit, descriptor.jsonKey, value)

	def run(self, edit):

		# known models are list of previously defined models.
		# If base model of some element exists on the list the plugin will use desinged initializer 
		# '-initWithJSON:' for super class instead of simple '-init'
		self.knownModels = list()

		allContentRegion = sublime.Region(0, self.view.size())
		if not allContentRegion.empty():
			# settings
			settingsJSON = self.view.settings().get(models.KEY_SETTINGS_CONVERSION_SETTINGS, dict())
			
			# Get file content
			text = self.view.substr(allContentRegion)

			try:
				jsonObj = sublime.decode_value(text)

				# print("JSON: {}".format(models.pretty_printed(jsonObj)))

				# direct settings dictionary from processed json file
				if  type(jsonObj) is dict:
					if models.KEY_TEMPLATE_CONVERSION_SETTINGS in jsonObj:
						explicit_settings = jsonObj[models.KEY_TEMPLATE_CONVERSION_SETTINGS]
						if explicit_settings:
							settingsJSON.update(explicit_settings)
						jsonObj = jsonObj[models.KEY_TEMPLATE_MODEL_JSON]

				# plugin settings object
				self.conversionSettings = models.ConversionSettings(settingsJSON)

				# generate models files
				self.generate_files(edit, self.conversionSettings.defaultRootModelClass, jsonObj)
			
			except Exception:
				self.show_exception()
