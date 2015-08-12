import os, sys, string, re

SOURCE_KEY_MODEL_CLASS_NAME      = "__CLASS_NAME__"
SOURCE_KEY_MODEL_BASE_CLASS_NAME = "__BASE_CLASS_NAME__"
KEY_DESCRIPTOR_SUBDESCRIPTORS    = "subdescriptors"
KEY_SETTINGS_CONVERSION_SETTINGS = "conversion_settings"

def to_camel_case(s):
    return s[0].lower() + string.capwords(s, sep='_').replace('_', '')[1:] if s else s

def to_snake_case(s):
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()

class ConversionSettings(dict):
    def __init__(self, settings):
        super(ConversionSettings, self).__init__()
        if type(settings) is dict:
            self.unknownPropertyName                     = "<#property_name#>"
            self.unknownClassName                        = "<#class_name#>"
            
            self.json                                    = settings
            self.arcEnabled                              = False
            self.numberAsObject                          = False
            self.booleanAsObject                         = False
            self.copyAsStringReferenceType               = False
            self.addSynthesizeClause                     = True
            self.addPropeertyNameConstants               = False
            self.leaveSourceJsonAsComment                = True
            self.defaultRootClass                        = "NSObject"
            self.hFileTemplate                           = ""
            self.mFileTemplate                           = ""
            self.commentTemplate                         = ""
            self.propertyDeclarationTemplate             = ""
            self.synthesizeTemplate                      = ""
            self.deallocMethodTemplate                   = ""
            self.deallocReferenceRemovingTemplate        = ""
            self.propertyInitializationTemplate          = ""
            self.nonObjectPropertyInitializationTemplate = ""
            
            for key, value in iter(settings.items()):
                print("property: {} ({})".format(to_camel_case(key), key))
                propertyName = to_camel_case(key)
                setattr(self, propertyName, value) # if propertyName in vars(self)

            self.initArgumentName = "json_" if self.addSynthesizeClause else "json"
            self.weakRefName = "weak" if self.arcEnabled else "assign"
            self.strongRefName = "strong" if self.arcEnabled else "retain"

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

        
class Default(dict):
    def __missing__(self, key):
        return "<#{}#>".format(to_snake_case(key))

class TokensMap(Default):

    def __getattr__(self, key):
        key = to_snake_case(key)# "<#{}#>".format(to_snake_case(key))
        return self[key]

    def __setattr__(self, key, value):
        key = to_snake_case(key)# "<#{}#>".format(to_snake_case(key))
        self[key] = value

class TransparentTokensMap(TokensMap):
    def __missing__(self, key):
        return "${{{}}}".format(to_snake_case(key))

class PropertyDescriptor(Default):

    """docstring for PropertyDescriptor"""
    def __init__(self, name, value, settings):
        super(PropertyDescriptor, self).__init__()
        self.name = name
        self.value = value
        self.valueType = type(value)

        if self.valueType is list:
            self.referenceType = settings.strongRefName
            self.type       = "NSArray*"
            # descriptor[KEY_DESCRIPTOR_SUBDESCRIPTORS]   = self.propertyDescriptorsForJSON(value)

        elif self.valueType is dict:
            self.referenceType   = settings.strongRefName
            self.type       = "NSDictionary*"
            # descriptor[KEY_DESCRIPTOR_SUBDESCRIPTORS]   = self.propertyDescriptorsForJSON(value)

        elif self.valueType is str:
            self.referenceType   = "copy" if settings.copyAsStringReferenceType else settings.strongRefName
            self.type       = "NSString*"

        elif self.valueType is int:
            if settings.numberAsObject:
                self.referenceType   = settings.strongRefName
                self.type       = "NSNumber*"
            else:
                self.valueGetterName = "integerValue"
                self.referenceType   = settings.weakRefName
                self.type       = "NSInteger"
                if len(self.deallocReferenceRemoving):
                    self.deallocReferenceRemoving = ""

        elif self.valueType is float:
            if settings.numberAsObject:
                self.referenceType   = settings.strongRefName
                self.type       = "NSNumber*"
            else:
                self.valueGetterName = "floatValue"
                self.referenceType   = settings.weakRefName
                self.type       = "CGFloat"
                if len(self.deallocReferenceRemoving):
                    self.deallocReferenceRemoving = ""

        elif self.valueType is bool:
            if settings.booleanAsObject:
                self.referenceType   = settings.strongRefName
                self.type       = "NSNumber*"
            else:
                self.valueGetterName = "boolValue"
                self.referenceType   = settings.weakRefName
                self.type       = "BOOL"
                if len(self.deallocReferenceRemoving):
                    self.deallocReferenceRemoving = ""

        else:
            self.referenceType   = settings.strongRefName
            self.type       = "id"

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


# def logBasicEnviromentProperties(self):

#     print("view.buffer_id() = {}".format(self.view.buffer_id()))
#     print("view.file_name() = {}".format(self.view.file_name()))
#     print("view.name() = {}".format(self.view.name()))
#     print("view.is_loading() = {}".format(self.view.is_loading()))
#     print("view.is_dirty() = {}".format(self.view.is_dirty()))
#     print("view.is_read_only() = {}".format(self.view.is_read_only()))
#     print("view.is_scratch() = {}".format(self.view.is_scratch()))
#     print("view.settings() = {}".format(self.view.settings()))

#     print("self.view.settings().get('{0}') = {1}".format(constants.KEY_SETTINGS_CONVERSION_SETTINGS, self.view.settings().get(constants.KEY_SETTINGS_CONVERSION_SETTINGS)))

#     print("view.window() = {}".format(self.view.window()))

#     print("\tview.window().id() = {}".format(self.view.window().id()))
#     # print("\tview.window().new_file() = {}".format(self.view.window().new_file()))
#     print("\tview.window().active_view() = {}".format(self.view.window().active_view()))
#     print("\tview.window().views() = {}".format(self.view.window().views()))
#     print("\tview.window().num_groups() = {}".format(self.view.window().num_groups()))
#     print("\tview.window().active_group() = {}".format(self.view.window().active_group()))
#     print("\tview.window().folders() = {}".format(self.view.window().folders()))
#     print("\tview.window().project_file_name() = {}".format(self.view.window().project_file_name()))
#     print("\tview.window().project_data() = {}".format(self.view.window().project_data()))
#     print("\tview.window().extract_variables() = {}".format(self.view.window().extract_variables()))

#     print("view.size() = {}".format(self.view.size()))
#     print("view.sel() = {}".format(self.view.sel()))
#     print("view.visible_region() = {}".format(self.view.visible_region()))
#     print("view.viewport_position() = {}".format(self.view.viewport_position()))
#     print("view.viewport_extent() = {}".format(self.view.viewport_extent()))
#     print("view.layout_extent() = {}".format(self.view.layout_extent()))
#     print("view.line_height() = {}".format(self.view.line_height()))
#     print("view.em_width() = {}".format(self.view.em_width()))
#     print("view.change_count() = {}".format(self.view.change_count()))
#     print("view.encoding() = {}".format(self.view.encoding()))
#     print("view.line_endings() = {}".format(self.view.line_endings()))
#     print("view.overwrite_status() = {}".format(self.view.overwrite_status()))