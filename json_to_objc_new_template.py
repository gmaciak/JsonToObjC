import json, datetime, sys, os

#sys.path.append(os.path.join(os.path.dirname(__file__), "modules"))
sys.path.append(os.path.dirname(__file__))
from json_to_objc_models_and_constants import *

class JsonToObjcNewTemplateCommand(JsonToObjcBaseCommand):

	def add_model_names_to_json(self, json, className = None):
		if className:
			className = ConversionSettings.to_pascal_case(className)
		if type(json) is dict:
			for key in json:
				self.add_model_names_to_json(json[key], key)
			if SOURCE_KEY_MODEL_CLASS_NAME not in json:
				if className:
					json[SOURCE_KEY_MODEL_CLASS_NAME] = className
				else:
					json[SOURCE_KEY_MODEL_CLASS_NAME] = self.conversionSettings.unknownClassName
			if SOURCE_KEY_MODEL_BASE_CLASS_NAME not in json:
				json[SOURCE_KEY_MODEL_BASE_CLASS_NAME] = self.conversionSettings.defaultRootClass

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
		settingsJSON = self.view.settings().get(KEY_SETTINGS_CONVERSION_SETTINGS, dict())
		self.conversionSettings = ConversionSettings(settingsJSON)

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
						if KEY_TEMPLATE_CONVERSION_SETTINGS in jsonObj:
							if KEY_TEMPLATE_MODEL_JSON in jsonObj:
								jsonObj = jsonObj[KEY_TEMPLATE_MODEL_JSON]
							else:
								message = str("'Invalid json !!!"
								"\n\tJSON contains {} key but {} key is missing."
								"\n\tPlease try to generate template again using source json'"
								).format(KEY_TEMPLATE_CONVERSION_SETTINGS,KEY_TEMPLATE_MODEL_JSON)
								raise ValueError(message)
						self.validate_values_and_keys(jsonObj)
						self.add_model_names_to_json(jsonObj, self.conversionSettings.defaultRootModelClass)
						model_json = pretty_printed(jsonObj)
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
		self.change_syntax(newFileView, "json");

		# template text
		templateString ="""{
	// Change following settings if needed
	"${settings_token}" : ${settings},

	// Replace following node value with JSON you want to convert.
	// Add key "${class_name_token}" to each json dictionary to define model class name.
	// Add key "${base_class_name_token}" to each json dictionary to define model base
	// class name (default model base class is NSObject).
	// In lists of objects if some values are null you should assign to them some
	// example value in one of the objects to determine the type of the value.
	"${model_json_token}" : ${json}
}
"""
		tokensMap = TokensMap()
		tokensMap.settingsToken = KEY_TEMPLATE_CONVERSION_SETTINGS
		tokensMap.settings = pretty_printed(settingsJSON).rstrip().replace("\n","\n\t")
		tokensMap.classNameToken = SOURCE_KEY_MODEL_CLASS_NAME
		tokensMap.baseClassNameToken = SOURCE_KEY_MODEL_BASE_CLASS_NAME
		tokensMap.modelJsonToken = KEY_TEMPLATE_MODEL_JSON
		tokensMap.json = model_json.replace("\n","\n\t")
		templateContent = string.Template(templateString).substitute(tokensMap)

		newFileView.insert(edit, 0, templateContent)