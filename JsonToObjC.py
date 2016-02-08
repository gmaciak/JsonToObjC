import json, datetime, sys, os

#sys.path.append(os.path.join(os.path.dirname(__file__), "modules"))
sys.path.append(os.path.dirname(__file__))
from json_to_objc_new_template import *
# from json_to_objc_models_and_constants import *

class JsonToObjcCommand(JsonToObjcBaseCommand):

	def run(self, edit, **kvargs):
		allContentRegion = sublime.Region(0, self.view.size())
		if not allContentRegion.empty():
			# settings
			# try to load settings from args if provided
			if KEY_SETTINGS_CONVERSION_SETTINGS in kvargs:
				settingsJSON = kvargs[KEY_SETTINGS_CONVERSION_SETTINGS]
				if type(settingsJSON) is not dict:
					settingsJSON = None;

			# load default settings if not provided in args
			if settingsJSON == None:
				settingsJSON = self.view.settings().get(KEY_SETTINGS_CONVERSION_SETTINGS, dict())
			
			
			# Get file content
			text = self.view.substr(allContentRegion)

			try:
				# decode json
				jsonObj = sublime.decode_value(text)

				# direct settings dictionary from processed json file
				if  type(jsonObj) is dict:
					if KEY_TEMPLATE_CONVERSION_SETTINGS in jsonObj:
						explicit_settings = jsonObj[KEY_TEMPLATE_CONVERSION_SETTINGS]
						if explicit_settings:
							settingsJSON.update(explicit_settings)
						jsonObj = jsonObj[KEY_TEMPLATE_MODEL_JSON]

				# plugin settings object
				self.conversionSettings = ConversionSettings(settingsJSON)

				# generate models list
				self.knownModelsList = list()
				self.describe_models_tree(edit, self.conversionSettings.defaultRootModelClass, jsonObj)

				# update base class names
				for descriptors in self.knownModelsList:
					baseClassName = descriptors.baseClassName
					if baseClassName is None:
						# base class not defined by user
						baseClassName = self.conversionSettings.defaultRootClass
					elif next((x for x in self.knownModelsList if x.className == self.prefixed_class_name(baseClassName)), None) is not None:
						# base class is a known model
						baseClassName = self.prefixed_class_name(baseClassName)

					if (baseClassName is not None
						and baseClassName != self.conversionSettings.unknownClassName):
						descriptors.baseClassName = baseClassName
				
				for x in self.knownModelsList:
					print("\t {}:{}".format(x.className,x.baseClassName))

				# known models are dictonary of models descriptors stored by
				# its class name after merge
				self.knownModels = dict()

				# merge repeted models
				while len(self.knownModelsList) > 0:
					self.add_or_merge_model(self.knownModelsList.pop())

				# remove inherited properties
				for value in self.knownModels.values():
					self.remove_inherited_properties(value, value.baseClassName)

				# generate models files
				self.generate_files(edit)
			
			except Exception as ex:
				self.show_exception()
				raise ex

	def default_tokens_replacements_map(self, className):
		"""  """
		defaultMap = TokensMap()
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

	def prefixed_class_name(self, className):
		return "{}{}".format(self.conversionSettings.classNamePrefix, className)

	def pop_descriptor_property_value(self, descriptors, propertyName):
		"""  """
		result = None
		for descriptor in descriptors:
			if descriptor.jsonKey == propertyName:
				result = descriptor.value
				descriptors.remove(descriptor)
				break
		return result;

	def interface_code(self, descriptors):
		"""  """
		propertiesDeclaration 	= str()
		className = descriptors.className
		baseClassName = descriptors.baseClassName;
		isSubclassOfKnownModel = className in self.knownModels

		# property declaration template tokens replacements
		tokensMap = TokensMap()
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
			propertiesDeclaration = "// No properties\n"

		# interface template tokens replacements
		tokensMap = self.default_tokens_replacements_map(className)

		# copy rights
		if self.conversionSettings.addStandardCopyrightComment:
			tokensMap.copyright = string.Template(
				self.conversionSettings.templateHCopyrightComment).safe_substitute(tokensMap)
		else:
			tokensMap.copyright = ""

		# base class
		if baseClassName is not None:
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

	def implementation_code(self, descriptors):
		"""  """
		syntesizeSection = str()
		initSection 	= str()
		deallocSection = str()
		className = descriptors.className
		isSubclassOfKnownModel = className in self.knownModels

		# variable for property initializer template
		templateInit = str()
		
		# propertis initialization (content of init method)
		initTokensMap = TokensMap()
		initTokensMap.jsonDictionaryName = self.conversionSettings.initArgumentName
		for descriptor in descriptors:
			initTokensMap.name = descriptor.name
			initTokensMap.jsonKey = descriptor.jsonKey
			initTokensMap.valueGetterName = descriptor.valueGetterName 

			if self.conversionSettings.addSynthesizeClause:
				initTokensMap.ivar = descriptor.name
			else:
				initTokensMap.ivar = "_{}".format(descriptor.name)

			# add synthesize for property (not in "if" above so you can use
			# 'ivar' token in synthesize like: @synthesize ${name} = _${ivar};)
			if self.conversionSettings.addSynthesizeClause:
				syntesizeSection += string.Template(self.conversionSettings.templateMSynthesize).safe_substitute(initTokensMap)
			
			# non object types
			if (((descriptor.valueType is int or descriptor.valueType is float) and not self.conversionSettings.numberAsObject) or
				(descriptor.valueType is bool and not self.conversionSettings.booleanAsObject)):
				if self.conversionSettings.arcEnabled:
					templateInit = self.conversionSettings.templateMArcNonObjectPropertyInitialization
				else:
					templateInit = self.conversionSettings.templateMNonObjectPropertyInitialization
			# object types
			else:
				# ARC
				if self.conversionSettings.arcEnabled:
					if descriptor.referenceType == self.conversionSettings.copyRefName:
						templateInit = self.conversionSettings.templateMArcCopyPropertyInitialization
					else:
						templateInit = self.conversionSettings.templateMArcStrongPropertyInitialization
				# MRC
				else:
					templateInit = self.conversionSettings.templateMPropertyInitialization
				if descriptor.isNullable and self.conversionSettings.useNilInsteadOfNullObject:
					templateInit += self.conversionSettings.templateMNullablePropertyUpdate

				# dealloc method content
				deallocSection += string.Template(self.conversionSettings.templateMDeallocReferenceRemoving).safe_substitute(initTokensMap)

			# add property initialization to init method content
			initSection += string.Template(templateInit).safe_substitute(initTokensMap)

		# interface template tokens replacements
		tokensMap = self.default_tokens_replacements_map(className)

		# copy rights
		if self.conversionSettings.addStandardCopyrightComment:
			tokensMap.copyright = string.Template(
				self.conversionSettings.templateMCopyrightComment).safe_substitute(tokensMap)
		else:
			tokensMap.copyright = ""
			
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
		methodsTokensMap = TransparentTokensMap()
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

	def describe_models_tree(self, edit, jsonKey, jsonObj):
		"""  """
		# json descriptors
		descriptors = DescriptorsList(jsonObj, self.conversionSettings)
		if self.conversionSettings.sortPropertiesByName:
			descriptors.sort(key=lambda descriptor: descriptor.name)

		if len(descriptors) > 0:
			# model class name
			className = self.pop_descriptor_property_value(
				descriptors,
				SOURCE_KEY_MODEL_CLASS_NAME)
			if (className is None):
				if (self.conversionSettings.allowPropertyKeyAsClassName
					and jsonKey is not None):
					className = TextConverterCommand.to_pascal_case(jsonKey)
					className = self.prefixed_class_name(className)
				else:
					print("default class name: ", Default().className)
					className = Default().className
			else:
				className = self.prefixed_class_name(className)

			if (className is not None
				and className != self.conversionSettings.unknownClassName):
				descriptors.className = className

			# model base class name
			descriptors.baseClassName = self.pop_descriptor_property_value(
				descriptors,
				SOURCE_KEY_MODEL_BASE_CLASS_NAME)
			
			self.knownModelsList.append(descriptors)

			# recursively other mothels in the tree
			for descriptor in descriptors:
				if "value" in descriptor:
					value = descriptor.value
					if type(value) is dict or type(value) is list:
						self.describe_models_tree(edit, descriptor.jsonKey, value)

	def add_or_merge_model(self, descriptors):
		className = descriptors.className

		if className in self.knownModels:
			existingModel = self.knownModels[className]
			
			if existingModel.baseClassName != descriptors.baseClassName:
				if existingModel.baseClassName is None:
					existingModel.baseClassName = descriptors.className
				elif descriptors.baseClassName is None:
					pass
				else:
					raise ValueError("Different base classes for"
							"the same class name\n\tClass name: {}"
							"\n\tBase class names: {}, {}".format(className,
								existingModel.baseClassName,
								descriptors.baseClassName))

			existingModel.merge(descriptors)
		else:
			# merge base classes in first place
			notMergedBase = next((x for x in self.knownModelsList if x.className == descriptors.baseClassName), None)
			while notMergedBase is not None:
				self.knownModelsList.remove(notMergedBase)
				self.add_or_merge_model(notMergedBase)
				notMergedBase = next((x for x in self.knownModelsList if x.className == descriptors.baseClassName), None)

			self.knownModels[className] = descriptors
	
	def remove_inherited_properties(self, descriptors, baseClassName):
		print("descriptors ",descriptors.className, ": ",descriptors.baseClassName, ": ", descriptors)
		if not descriptors.inheritanceChecked:
			if baseClassName is not None and baseClassName in self.knownModels:
				inheritedDescriptors = self.knownModels[baseClassName]
				for base in inheritedDescriptors :
					sub = next((x for x in descriptors if x.name == base.name), None)
					if sub is not None:
						if sub.isNullable:
							base.isNullable = True
						if sub.isAnObject == base.isAnObject:
							if base.type != sub.type:
								if base.type == TYPE_OBJECT:
									# inherited property type is not known yet
									if not base.isTypeDetermined:
										base.type = sub.type
										base.valueType = sub.valueType
								# inherited property type is known
								# but inheriting class property type is unknown
								elif sub.type == TYPE_OBJECT and not sub.isTypeDetermined:
									pass
								else:
									# inherited property type is known and different
									# then the one in inheriting class
									base.type = TYPE_OBJECT
									base.valueType = type(None)
									base.isTypeDetermined = True

						# inheriting class property has simple type
						elif base.isAnObject and base.type != TYPE_NUMBER:
							# diferent types
							base.type = TYPE_OBJECT
							base.valueType = type(None)
							base.isTypeDetermined = True

						# inherited class property has simple value
						elif sub.isAnObject:
							if sub.type == TYPE_NUMBER:
								base.type = sub.type
								base.valueType = sub.valueType
							else:
								base.type = TYPE_OBJECT
								base.valueType = type(None)
								base.isTypeDetermined = True
							base.valueGetterName = None
							base.referenceType = self.conversionSettings.strongRefName
							base.isAnObject = True
						descriptors.remove(sub)

				# recursively delete any properties from other ancestors
				self.remove_inherited_properties(descriptors, inheritedDescriptors.baseClassName)
			# mark incheritance check as completed to avoid redundant checking
			descriptors.inheritanceChecked = True

	def generate_files(self, edit):
		"""  """
		for descriptors in self.knownModels.values():
			if self.conversionSettings.sortPropertiesByName:
				descriptors.sort(key=lambda descriptor: descriptor.name)

			if len(descriptors) > 0 or descriptors.baseClassName in self.knownModels:

				fileName = None
				if descriptors.className and descriptors.className != self.conversionSettings.unknownClassName:
					fileName = descriptors.className

				# Interface code
				interfaceCode = self.interface_code(descriptors)

				# Implementation code
				implementationCode = self.implementation_code(descriptors)
				
				# Interface file (.h)
				newFileView = self.view.window().new_file()
				newFileView.insert(edit, 0, interfaceCode)

				if fileName is not None:
					newFileView.set_name("{}.h".format(fileName))
				self.change_syntax(newFileView, "objc")

				# Implementation file (.m)
				newFileView = self.view.window().new_file()
				newFileView.insert(edit, 0, implementationCode)

				if fileName is not None:
					newFileView.set_name("{}.m".format(fileName))
				self.change_syntax(newFileView, "objc")

class JsonToObjcPrettyPrintCommand(TextConverterCommand):
	def run(self, edit):
		selection = self.view.sel()
		for region in selection:
			region_text = self.view.substr(region)
			print("region_text",region_text)
			try:
				obj = sublime.decode_value(region_text)
				print("obj",obj)
				converted_text = sublime.encode_value(obj, True)
				self.view.replace(edit, region, converted_text)
			except ValueError as err:
				print("ValueError",err)
				self.show_exception()