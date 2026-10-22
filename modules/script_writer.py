import importlib
_mod = importlib.import_module("modules.2_script_writer")
generate_shopee_script = _mod.generate_shopee_script
build_script_prompt = _mod.build_script_prompt
ShopeeScriptResult = _mod.ShopeeScriptResult
