Under construction...

# JsonToObjC
Sublime 3 plugin to generate Objective-C data models from JSON

## Install:

1. Clone or dwonload and unzip the files to Sublime Text 3 Packages directory:  
  `~/Library/Application\ Support/Sublime\ Text\ 3/Packages/JsonToObjC`

2. You may need to restart the Sublime Text 3 to reload the plugins
3. Now you should have `JSON to Objective-C (JTOC)` commands available from the context menu.

## Using default generator

To try the plugin you can open any valid JSON file, it may be for example default plugin configuration
which you can find in Sublime Text main menu `Sublime Text/Preferences/JSON to Objective-C/Settings - Default`

1. Open JSON file in Sublime Text 3
2. Click ther right mouse button (open context menu) anywere in the window/tab.
3. Select `JSON to Objective-C (JTOC)/Generate Models`

JTOC plugin will open different tab for each .h and .m file for every model so you can see the result and save needed models files.


# Configure your own generator

You can easely, or maybe not that easly configure your own model generator.
Tere are three ways to do that.

1. Modifying and overriding default configuration.
  To do so:
  * Open `Settings - Default` file using Sublime Text Main Menu:

    	`Sublime Text/Preferences/JSON to Objective-C/Settings - Default`
    
  * Copy whole JSON text to clipboard
  * Open `Settings - User` file
  
    	`Sublime Text/Preferences/JSON to Objective-C/Settings - User`
    
  * Paste previously copied json to the newly opened tab/file
  * Modyfy settings as you need.
  * Save user settings (Command+S)
  
2. Creating your own context-menu command. In this case conversion settings might be given as a command parameter.

3. Generating a Conversion Template File.

## Default generator configuration

You can find default donfiguration of the plugin in menu  
`Sublime Text/Preferences/JSON to Objective-C/Settings - Default`  
and it looks like this:

```JavaScript
{
	"conversion_settings" : {
		// default model root class
		"default_root_class"			: "NSObject",

		// class of main json object used if optional
		// @CLASS_NAME key in main json object is not defined 
		"default_root_model_class"		: "RootModel",
		"arc_enabled"					: true,
		"number_as_object"				: true,
		"boolean_as_object"				: true,

		// use property key istead of default model class name
		// (which is xcode snipped token <#class_name#>)
		// if @CLASS_NAME not defined
		"allow_property_key_as_class_name" : true,

		// by default property names are created from keys by converting to camel case and removeing undersocres
		"use_json_keys_as_property_names" : false,

		// for nullable objects set property to nil instead of NSNull, default is true
		"use_nil_instead_of_null_object" : true,

		// use copy instead retain or strong for strings:
		"copy_as_string_reference_type"	: true,

		// add @synthesize for properties, implicitly synthesized property has ivar name '_propertyName', when explicitly synthesized has ivar name "propertyName"
		"add_synthesize_clause"			: false,

		"add_standard_copyright_comment": true,

		"sort_properties_by_name"		: true,

		// Templates. If you change them do it carefully:
		"template_h_file"				: "${copyright}#import <Foundation/Foundation.h>\n\nNS_ASSUME_NONNULL_BEGIN\n@interface ${class_name} : ${base_class_name}\n\n${properties_declaration}\n${designed_initializer}@end\nNS_ASSUME_NONNULL_END",

		"template_h_copyright_comment"	: "//\n//  ${class_name}.h\n//  ${project_name}\n//\n//  Created by ${creator} on ${date}.\n//  Copyright (c) ${year} ${organization}. All rights reserved.\n//\n\n",

		"template_h_property" : "@property(nonatomic,${reference_type}) ${type} ${name};\n",

		"template_h_designed_initializer" : "-(instancetype)initWithJSON:(nullable NSDictionary*)json;\n\n",

		"template_m_file"				: "${copyright}#import \"${class_name}.h\"\n\n@implementation ${class_name}\n\n${synthesizes}${dealloc}-(id)initWithJSON:(NSDictionary*)${json_dictionary_name} {\n\tself = ${super_init_method};\n\tif (self) {\n${init_content}\t}\n\treturn self;\n}\n\n@end",

		"template_m_copyright_comment"	: "//\n//  ${class_name}.m\n//  ${project_name}\n//\n//  Created by ${creator} on ${date}.\n//  Copyright (c) ${year} ${organization}. All rights reserved.\n//\n\n",

		"template_m_default_super_init_method" : "[super init]",
		"template_m_inherited_super_init_method" : "[super initWithJSON:${json_dictionary_name}]",

		// dealloc templates
		"template_m_dealloc_method" 				: "-(void)dealloc {\n${dealloc_code}\t[super dealloc];\n}\n\n",

		"template_m_dealloc_reference_removing" : "\tself.${name} = nil;\n",

		"template_m_synthesize" : "@synthesize ${name};\n",

		"template_m_property_initialization" : "\t\tself.${name} = [${json_dictionary_name} objectForKey:@\"${json_key}\"];\n",
		"template_m_non_object_property_initialization" : "\t\tself.${name} = [[${json_dictionary_name} objectForKey:@\"${json_key}\"] ${value_getter_name}];\n",

		"template_m_arc_strong_property_initialization" : "\t\t${ivar} = [${json_dictionary_name} objectForKey:@\"${json_key}\"];\n",
		"template_m_arc_copy_property_initialization" : "\t\t${ivar} = [[${json_dictionary_name} objectForKey:@\"${json_key}\"] copy];\n",
		"template_m_arc_non_object_property_initialization" : "\t\t${ivar} = [[${json_dictionary_name} objectForKey:@\"${json_key}\"] ${value_getter_name}];\n",

		"template_m_nullable_property_update" : "\t\tif ([self.${name} isKindOfClass:[NSNull class]]) self.${name} = nil;\n",

		// optional:
		"project_name" 					: "__PROJECT_NAME__",
		"creator" 						: "__CREATOR__",
		"organization" 					: "__ORGANIZATION__",
	}
}
```
### Available tokens:
```
base_class_name, class_name, copyright, creator, date, dealloc_code, dealloc,
designed_initializer,  init_content, ivar, json_dictionary_name, json_key,
name, organization, project_name, properties_declaration, reference_type,
super_init_method, synthesizes, type, value_getter_name, year
```

`${base_class_name}` - replaced by base class name or `default_root_class` value.  
`${class_name}` - replaced by class name created according to the settings.  
`${copyright}` - replaced with   
`${creator}` - replaced with   
`${date}` - replaced with   
`${dealloc_code}` - replaced with   
`${dealloc}` - replaced with   
`${designed_initializer}` - replaced with   
`${init_content}` - replaced with   
`${ivar}` - replaced with   
`${json_dictionary_name}` - replaced with   
`${json_key}` - replaced with   
`${name}` - replaced with   
`${organization}` - replaced with   
`${project_name}` - replaced with   
`${properties_declaration}` - replaced with   
`${reference_type}` - replaced with   
`${super_init_method}` - replaced with   
`${synthesizes}` - replaced with   
`${type}` - replaced with   
`${value_getter_name}` - replaced with   
`${year}` - replaced with   