import os, sys, string, re, sublime, sublime_plugin

SOURCE_KEY_MODEL_CLASS_NAME      = "@CLASS_NAME"
SOURCE_KEY_MODEL_BASE_CLASS_NAME = "@BASE_CLASS_NAME"
KEY_SETTINGS_CONVERSION_SETTINGS = "conversion_settings"
KEY_TEMPLATE_CONVERSION_SETTINGS = "@CONVERSION_SETTINGS"
KEY_TEMPLATE_MODEL_JSON          = "@MODEL_JSON"

def pretty_printed(value):
    return sublime.encode_value(value, True)

class JsonToObjcBaseCommand(sublime_plugin.TextCommand):
    """ Model generator command base class """
    def change_syntax(self, view = None):
        """ Changes syntax to JSON if it is plain text """
        if view is None:
            view = self.view
        if "Plain text" in view.settings().get('syntax'):
            view.set_syntax_file("Packages/JavaScript/JSON.tmLanguage")

    def show_exception(self):
        exc = sys.exc_info()[1]
        sublime.status_message(str(exc))

class JsonToObjcConvertCaseBaseCommand(JsonToObjcBaseCommand):
    """ Case converstion command base class """
    def preform_on_selection(self, edit, mehtod):
        selection = self.view.sel()
        for region in selection:
            region_text = self.view.substr(region)
            converted_text = mehtod(region_text)
            self.view.replace(edit, region, converted_text)

class Default(dict):
    """ Default plubin dictionary extension """
    
    @staticmethod
    def to_camel_case(s):
        if s and len(s) > 0:
            result = s[0].lower()
            if len(s) > 1:
                if "_" in s:
                    result += string.capwords(s, sep='_').replace('_', '')[1:]
                else:
                    result += s[1:]
            return result
        return s

    @staticmethod
    def to_snake_case(s):
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()

    @staticmethod
    def to_pascal_case(s):
        if s and len(s) > 0:
            result = s[0].upper()
            if len(s) > 1: result += Default.to_camel_case(s)[1:]
            return result
        return s

    def __missing__(self, key):
        """  """
        return "<#{}#>".format(self.to_snake_case(key))

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
            self.json                                       = settings
            self.arcEnabled                                 = False
            self.numberAsObject                             = False
            self.booleanAsObject                            = False
            self.allowPropertyKeyAsClassName                = True
            self.useJsonKeysAsPropertyNames                 = False
            self.copyAsStringReferenceType                  = False
            self.addSynthesizeClause                        = True
            self.addPropeertyNameConstants                  = False
            self.leaveSourceJsonAsComment                   = True
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
            
            # settings values (overrid the defaults)
            for key, value in iter(settings.items()):
                #print("property: {} ({})".format(self.to_camel_case(key), key))
                propertyName = self.to_camel_case(key)
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
        key = self.to_snake_case(key)
        return self[key]

    def __setattr__(self, key, value):
        key = self.to_snake_case(key)
        self[key] = value

class TransparentTokensMap(TokensMap):
    """  """
    def __missing__(self, key):
        return "${{{}}}".format(self.to_snake_case(key))

class PropertyDescriptor(Default):
    """Custom dictionary with descriptors of the single property"""
    
    def __init__(self, name, value, settings):
        super(PropertyDescriptor, self).__init__()
        self.jsonKey = name;
        if not settings.useJsonKeysAsPropertyNames and not name.startswith("@"):
            self.name = self.to_camel_case(name)
        else:
            self.name = name
        self.value = value
        self.valueType = type(value)
        self.isNullable = self.value is None

        #print("property: %s = %s (%s)".format(name,value,self.valueType))
        if self.valueType is list:
            self.referenceType      = settings.strongRefName
            self.type               = "NSArray*"

        elif self.valueType is dict:
            self.referenceType      = settings.strongRefName
            self.type               = "NSDictionary*"

        elif self.valueType is str:
            if settings.copyAsStringReferenceType:
                self.referenceType  = settings.copyRefName
            else:
                self.referenceType  = settings.strongRefName
            self.type               = "NSString*"

        elif self.valueType is int:
            if settings.numberAsObject:
                self.referenceType  = settings.strongRefName
                self.type           = "NSNumber*"
            else:
                self.valueGetterName = "integerValue"
                self.referenceType  = settings.weakRefName
                self.type           = "NSInteger"
                if self.deallocReferenceRemoving and len(self.deallocReferenceRemoving):
                    self.deallocReferenceRemoving = ""

        elif self.valueType is float:
            if settings.numberAsObject:
                self.referenceType  = settings.strongRefName
                self.type           = "NSNumber*"
            else:
                self.valueGetterName = "floatValue"
                self.referenceType  = settings.weakRefName
                self.type           = "CGFloat"
                if self.deallocReferenceRemoving and len(self.deallocReferenceRemoving):
                    self.deallocReferenceRemoving = ""

        elif self.valueType is bool:
            if settings.booleanAsObject:
                self.referenceType  = settings.strongRefName
                self.type           = "NSNumber*"
            else:
                self.valueGetterName = "boolValue"
                self.referenceType  = settings.weakRefName
                self.type           = "BOOL"
                if self.deallocReferenceRemoving and len(self.deallocReferenceRemoving):
                    self.deallocReferenceRemoving = ""

        else:
            self.referenceType   = settings.strongRefName
            self.type       = "id"

    def __getattr__(self, key):
        return self[key] if key in self else None

    def __setattr__(self, key, value):
        self[key] = value
