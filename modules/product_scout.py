import importlib
_mod = importlib.import_module("modules.1_product_scout")
scout_shopee_products = _mod.scout_shopee_products
extract_product_id = _mod.extract_product_id
scrape_shopee_product = _mod.scrape_shopee_product
update_products_db = _mod.update_products_db
