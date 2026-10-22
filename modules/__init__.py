import importlib

# Dynamic import helpers for numbered filenames
_scout = importlib.import_module("modules.1_product_scout")
_curator = importlib.import_module("modules.1_5_vision_curator")
_writer = importlib.import_module("modules.2_script_writer")
_voice = importlib.import_module("modules.3_voice_and_sub")
_assembler = importlib.import_module("modules.4_video_assembler")

scout_shopee_products = _scout.scout_shopee_products
curate_product_videos = _curator.curate_product_videos
generate_shopee_script = _writer.generate_shopee_script
generate_voiceover_and_subtitles = _voice.generate_voiceover_and_subtitles
assemble_curated_video = _assembler.assemble_curated_video

check_video_quality_local = _curator.check_video_quality_local
VideoSegment = _curator.VideoSegment
ClipAnalysisResult = _curator.ClipAnalysisResult
ShopeeScriptResult = _writer.ShopeeScriptResult

__all__ = [
    "scout_shopee_products",
    "curate_product_videos",
    "generate_shopee_script",
    "generate_voiceover_and_subtitles",
    "assemble_curated_video",
    "check_video_quality_local",
    "VideoSegment",
    "ClipAnalysisResult",
    "ShopeeScriptResult"
]
