## ClassDef DocItemType
dynamodocs/tree_handler.py/DocItemType - [DocItemType._class] : 
documentation to be generated
### FunctionDef to_str(self)
dynamodocs/tree_handler.py/DocItemType/to_str - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef print_self(self)
dynamodocs/tree_handler.py/DocItemType/print_self - [DocItemType._class_method] : 
documentation to be generated
***
## ClassDef DocItemStatus
dynamodocs/tree_handler.py/DocItemStatus - [DocItemType._class] : 
documentation to be generated
## ClassDef DocItem
dynamodocs/tree_handler.py/DocItem - [DocItemType._class] : 
documentation to be generated
### FunctionDef check_and_return_ancestor(doc1, doc2)
dynamodocs/tree_handler.py/DocItem/check_and_return_ancestor - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef need_to_generate(doc_item, ignore_list)
dynamodocs/tree_handler.py/DocItem/need_to_generate - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef check_has_task(doc, ignore_list)
dynamodocs/tree_handler.py/DocItem/check_has_task - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef get_preorder_traversal(self, _travel_list)
dynamodocs/tree_handler.py/DocItem/get_preorder_traversal - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef calculate_depth(self)
dynamodocs/tree_handler.py/DocItem/calculate_depth - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef parse_tree_path(self, now_path)
dynamodocs/tree_handler.py/DocItem/parse_tree_path - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef get_full_name(self, strict)
dynamodocs/tree_handler.py/DocItem/get_full_name - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef get_file_name(self)
dynamodocs/tree_handler.py/DocItem/get_file_name - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef find(self, recursive_file_path)
dynamodocs/tree_handler.py/DocItem/find - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef print_recursive(self, indent, print_content, diff_status, ignore_list)
dynamodocs/tree_handler.py/DocItem/print_recursive - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef print_indent(indent)
dynamodocs/tree_handler.py/DocItem/print_recursive/print_indent - [DocItemType._sub_function] : 
documentation to be generated
***
***
## FunctionDef find_all_referencer(repo_path, variable_name, file_path, line_number, column_number, in_file_only)
dynamodocs/tree_handler.py/find_all_referencer - [DocItemType._function] : 
documentation to be generated
## ClassDef MetaInfo
dynamodocs/tree_handler.py/MetaInfo - [DocItemType._class] : 
documentation to be generated
### FunctionDef init_meta_info(file_path_reflections, jump_files)
dynamodocs/tree_handler.py/MetaInfo/init_meta_info - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef from_checkpoint_path(checkpoint_dir_path)
dynamodocs/tree_handler.py/MetaInfo/from_checkpoint_path - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef checkpoint(self, target_dir_path, flash_reference_relation)
dynamodocs/tree_handler.py/MetaInfo/checkpoint - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef print_task_list(self, task_dict)
dynamodocs/tree_handler.py/MetaInfo/print_task_list - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef from_project_hierarchy_path(repo_path)
dynamodocs/tree_handler.py/MetaInfo/from_project_hierarchy_path - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef from_project_hierarchy_json(project_hierarchy_json)
dynamodocs/tree_handler.py/MetaInfo/from_project_hierarchy_json - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef change_items(now_item)
dynamodocs/tree_handler.py/MetaInfo/from_project_hierarchy_json/change_items - [DocItemType._sub_function] : 
documentation to be generated
***
#### FunctionDef code_contain(item, other_item)
dynamodocs/tree_handler.py/MetaInfo/from_project_hierarchy_json/code_contain - [DocItemType._sub_function] : 
documentation to be generated
***
***
### FunctionDef to_hierarchy_json(self, flash_reference_relation)
dynamodocs/tree_handler.py/MetaInfo/to_hierarchy_json - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef walk_file(now_obj)
dynamodocs/tree_handler.py/MetaInfo/to_hierarchy_json/walk_file - [DocItemType._sub_function] : 
documentation to be generated
***
***
### FunctionDef from_project_hierarchy_path(repo_path)
dynamodocs/tree_handler.py/MetaInfo/from_project_hierarchy_path - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef get_all_files(self)
dynamodocs/tree_handler.py/MetaInfo/get_all_files - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef walk_tree(now_node)
dynamodocs/tree_handler.py/MetaInfo/get_all_files/walk_tree - [DocItemType._sub_function] : 
documentation to be generated
***
***
### FunctionDef find_obj_with_lineno(self, file_node, start_line_num)
dynamodocs/tree_handler.py/MetaInfo/find_obj_with_lineno - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef parse_reference(self)
dynamodocs/tree_handler.py/MetaInfo/parse_reference - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef walk_file(now_obj)
dynamodocs/tree_handler.py/MetaInfo/parse_reference/walk_file - [DocItemType._sub_function] : 
documentation to be generated
***
***
### FunctionDef get_task_manager(self, now_node, task_available_func)
dynamodocs/tree_handler.py/MetaInfo/get_task_manager - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef in_white_list(item)
dynamodocs/tree_handler.py/MetaInfo/get_task_manager/in_white_list - [DocItemType._sub_function] : 
documentation to be generated
***
***
### FunctionDef get_topology(self, task_available_func)
dynamodocs/tree_handler.py/MetaInfo/get_topology - [DocItemType._class_method] : 
documentation to be generated
***
### FunctionDef load_doc_from_older_meta(self, older_meta)
dynamodocs/tree_handler.py/MetaInfo/load_doc_from_older_meta - [DocItemType._class_method] : 
documentation to be generated
#### FunctionDef find_item(now_item)
dynamodocs/tree_handler.py/MetaInfo/load_doc_from_older_meta/find_item - [DocItemType._sub_function] : 
documentation to be generated
***
#### FunctionDef travel(now_older_item)
dynamodocs/tree_handler.py/MetaInfo/load_doc_from_older_meta/travel - [DocItemType._sub_function] : 
documentation to be generated
***
#### FunctionDef travel2(now_older_item)
dynamodocs/tree_handler.py/MetaInfo/load_doc_from_older_meta/travel2 - [DocItemType._sub_function] : 
documentation to be generated
***
***
