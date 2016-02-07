import sublime, sublime_plugin, string, re, sys, os

SOURCE_KEY_MODEL_CLASS_NAME      = "@CLASS_NAME"
SOURCE_KEY_MODEL_BASE_CLASS_NAME = "@BASE_CLASS_NAME"
KEY_SETTINGS_CONVERSION_SETTINGS = "conversion_settings"
KEY_TEMPLATE_CONVERSION_SETTINGS = "@CONVERSION_SETTINGS"
KEY_TEMPLATE_MODEL_JSON          = "@MODEL_JSON"
TYPE_LIST = "NSArray*"
TYPE_DICT = "NSDictionary*"
TYPE_STRING = "NSString*"
TYPE_NUMBER = "NSNumber*"
TYPE_OBJECT = "id"
TYPE_FLOAT = "CGFloat"
TYPE_INT = "NSInteger"
TYPE_BOOL = "BOOL"

sys.path.append(os.path.dirname(__file__))
from kk_text_converter import *

def pretty_printed(value):
	return sublime.encode_value(value, True)

class JsonToObjcBaseCommand(BasePluginCommand):
	pass

class Default(dict):
	""" Default plubin dictionary extension """

	def __missing__(self, key):
		"""  """
		return "<#{}#>".format(TextConverter.to_snake_case(key))

	def __getattr__(self, key):
		return self[key] if key in self else None

	def __setattr__(self, key, value):
		self[key] = value

class ConversionSettings(Default):
	"""  """
	def __init__(self, settings):
		super(ConversionSettings, self).__init__()
		if type(settings) is dict:
			# default values
			self.unknownPropertyName                        = "<#property_name#>"
			self.unknownClassName                           = "<#class_name#>"
			self.classNamePrefix                            = ""
			#self.json                                       = settings
			self.arcEnabled                                 = True
			self.numberAsObject                             = False
			self.booleanAsObject                            = False
			self.allowPropertyKeyAsClassName                = True
			self.useJsonKeysAsPropertyNames                 = False
			self.useNilInsteadOfNullObject					= True
			self.copyAsStringReferenceType                  = False
			self.addSynthesizeClause                        = False
			#self.addPropeertyNameConstants                  = False
			#self.leaveSourceJsonAsComment                   = True
			self.defaultRootClass                           = "NSObject"
			self.defaultRootModelClass                      = None
			self.sortPropertiesByName                       = True
			self.templateHFile                              = ""
			self.templateHComment                           = ""
			self.templateHProperty                          = ""
			self.templateHDesignedInitializer               = ""
			self.templateMFile                              = ""
			self.templateMComment                           = ""
			self.templateMSynthesize                        = ""
			self.templateMDeallocMethod                     = ""
			self.templateMDeallocReferenceRemoving          = ""
			self.templateMPropertyInitialization            = ""
			self.templateMNonObjectPropertyInitialization   = ""
			self.templateMArcStrongPropertyInitialization   = ""
			self.templateMArcCopyPropertyInitialization     = ""
			self.templateMArcNonObjectPropertyInitialization = ""
			self.templateMNullablePropertyUpdate			= ""
			
			# settings values (overrid the defaults)
			for key, value in iter(settings.items()):
				#print("property: {} ({})".format(TextConverterCommand.to_camel_case(key), key))
				propertyName = TextConverterCommand.to_camel_case(key)
				setattr(self, propertyName, value) # if propertyName in vars(self)

			# dependent values
			self.initArgumentName = "json_"     if self.addSynthesizeClause else "json"
			self.weakRefName      = "weak"      if self.arcEnabled else "assign"
			self.strongRefName    = "strong"    if self.arcEnabled else "retain"
			self.copyRefName      = "copy"

	def __missing__(self, key):
		"""  """
		return None

class TokensMap(Default):
	"""  """
	def __getattr__(self, key):
		key = TextConverterCommand.to_snake_case(key)
		return self[key]

	def __setattr__(self, key, value):
		key = TextConverterCommand.to_snake_case(key)
		self[key] = value

class TransparentTokensMap(TokensMap):
	"""  """
	def __missing__(self, key):
		return "${{{}}}".format(TextConverterCommand.to_snake_case(key))

class DescriptorsList(list):
	"""docstring for DescriptorsList"""
	def __init__(self, json = None, settings = None):
		super(DescriptorsList, self).__init__()
		self.className = None
		self.baseClassName = None
		self.inheritanceChecked = False
		if json is not None and settings is not None:
			self.create_descriptors(json, settings)
	
	def merge(self, descriptors):
		for item in descriptors:
			prevItem = next((x for x in self if x.jsonKey == item.jsonKey), None)
			
			if prevItem is None:
				# every missing property needs to be nullable
				item.isNullable = True
				# it is the first descriptor for the property
				self.append(item)
			# if one of property values shows that it can be null update
			# previewous property definition
			else:
				# if previous item is None the definition is not full,
				# for eg. value type is not specified, so
				# we should use new item which may be more precise
				if prevItem.valueType is type(None):
					if not item.isNullable:
						item.isNullable = prevItem.isNullable
					if not item.isAnObject:
						item.isAnObject = True
						self.referenceType = settings.strongRefName
						item.valueType = TYPE_NUMBER
						item.valueGetterName = None
					self.remove(prevItem)
					self.append(item)
				# if prev item value is not Null we can leave old definition
				elif item.isNullable or item.valueType is type(None):
					prevItem.isNullable = True;
					if not prevItem.isAnObject:
						prevItem.isAnObject = True
						self.referenceType = settings.strongRefName
						prevItem.valueType = TYPE_NUMBER
						prevItem.valueGetterName = None

		for item in self:
			newItem = next((x for x in descriptors if x.jsonKey == item.jsonKey), None)
			if newItem is None and not item.isNullable:
				# every property not present in new object needs to be nullable
				item.isNullable = True

	def create_descriptors(self, json, settings):
		# merge all subitems properties
		if type(json) is list and len(json) > 0:
			for obj in json:
				item_descriptors = DescriptorsList(obj, settings)
				self.merge(item_descriptors)

		elif type(json) is dict and len(json) > 0:
			for key in json:
				if key == "": continue
				value = json[key]
				self.append(PropertyDescriptor(key, value, settings))

class PropertyDescriptor(Default):
	"""Custom dictionary with descriptors of the single property"""
	
	def __init__(self, name, value, settings):
		super(PropertyDescriptor, self).__init__()
		self.jsonKey = name;
		if not settings.useJsonKeysAsPropertyNames and not name.startswith("@"):
			self.name = TextConverterCommand.to_camel_case(name)
		else:
			self.name = name
		self.value = value
		self.valueType = type(value)
		self.isNullable = settings.useNilInsteadOfNullObject and self.value is None
		self.isAnObject = True
		self.isTypeDetermined = True
		self.valueGetterName = None

		#print("property: %s = %s (%s)".format(name,value,self.valueType))
		if self.valueType is list:
			self.referenceType      = settings.strongRefName
			self.type               = TYPE_LIST

		elif self.valueType is dict:
			self.referenceType      = settings.strongRefName
			self.type               = TYPE_DICT

		elif self.valueType is str:
			if settings.copyAsStringReferenceType:
				self.referenceType  = settings.copyRefName
			else:
				self.referenceType  = settings.strongRefName
			self.type               = TYPE_STRING

		elif self.valueType is int:
			if settings.numberAsObject:
				self.referenceType  = settings.strongRefName
				self.type           = TYPE_NUMBER
			else:
				self.valueGetterName = "integerValue"
				self.referenceType  = settings.weakRefName
				self.type           = TYPE_INT
				self.isAnObject     = False
				if self.deallocReferenceRemoving and len(self.deallocReferenceRemoving):
					self.deallocReferenceRemoving = ""

		elif self.valueType is float:
			if settings.numberAsObject:
				self.referenceType  = settings.strongRefName
				self.type           = TYPE_NUMBER
			else:
				self.valueGetterName = "floatValue"
				self.referenceType  = settings.weakRefName
				self.type           = TYPE_FLOAT
				self.isAnObject     = False
				if self.deallocReferenceRemoving and len(self.deallocReferenceRemoving):
					self.deallocReferenceRemoving = ""

		elif self.valueType is bool:
			if settings.booleanAsObject:
				self.referenceType  = settings.strongRefName
				self.type           = TYPE_NUMBER
			else:
				self.valueGetterName = "boolValue"
				self.referenceType  = settings.weakRefName
				self.type           = TYPE_BOOL
				self.isAnObject     = False
				if self.deallocReferenceRemoving and len(self.deallocReferenceRemoving):
					self.deallocReferenceRemoving = ""

		else:
			self.referenceType   = settings.strongRefName
			self.type       = TYPE_OBJECT
			self.isTypeDetermined = False;

	def __getattr__(self, key):
		return self[key] if key in self else None

	def __setattr__(self, key, value):
		self[key] = value
